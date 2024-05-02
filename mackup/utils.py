"""System static utilities being used by the modules."""

from __future__ import annotations

import base64
import os
import platform
import shutil
import sqlite3
import stat
import subprocess  # noqa: S404
import sys
from pathlib import Path

from mackup import constants

# Flag that controls how user confirmation works.
# If True, the user wants to say "yes" to everything.
FORCE_YES = False

# Flag that control if mackup can be run as root
CAN_RUN_AS_ROOT = False


def confirm(question: str) -> bool:
    """
    Ask the user if he really wants something to happen.

    Args:
        question(str): What can happen

    Returns:
        (boolean): Confirmed or not
    """
    if FORCE_YES:
        return True

    while True:
        answer = input(question + " <Yes|No> ").lower()

        if answer in {"yes", "y"}:
            confirmed = True
            break
        if answer in {"no", "n"}:
            confirmed = False
            break

    return confirmed


def delete(filepath: str) -> None:
    """
    Delete the given file, directory or link.

    It Should support undelete later on.

    Args:
        filepath (str): Absolute full path to a file. e.g. /path/to/file
    """
    # Some files have ACLs, let's remove them recursively
    remove_acl(filepath)

    # Some files have immutable attributes, let's remove them recursively
    remove_immutable_attribute(filepath)

    # Finally remove the files and folders
    if Path(filepath).is_file() or Path(filepath).is_symlink():
        Path(filepath).unlink()
    elif Path(filepath).is_dir():
        shutil.rmtree(filepath)


def copy(src: str, dst: str) -> None:
    """
    Copy a file or a folder (recursively) from src to dst.

    For the sake of simplicity, both src and dst must be absolute path and must
    include the filename of the file or folder.
    Also do not include any trailing slash.

    e.g. copy('/path/to/src_file', '/path/to/dst_file')
    or copy('/path/to/src_folder', '/path/to/dst_folder')

    But not: copy('/path/to/src_file', 'path/to/')
    or copy('/path/to/src_folder/', '/path/to/dst_folder')

    Args:
        src (str): Source file or folder
        dst (str): Destination file or folder
    """
    assert isinstance(src, str)
    assert Path(src).exists()
    assert isinstance(dst, str)

    # Create the path to the dst file if it does not exist
    abs_path = Path(dst).resolve().parent
    if not abs_path.is_dir():
        abs_path.mkdir(parents=True, exist_ok=True)

    # We need to copy a single file
    if Path(src).is_file():
        # Copy the src file to dst
        shutil.copy(src, dst)

    # We need to copy a whole folder
    elif Path(src).is_dir():
        shutil.copytree(src, dst)

    # What the heck is this?
    else:
        msg = f"Unsupported file: {src}"
        raise ValueError(msg)

    # Set the good mode to the file or folder recursively
    chmod(dst)


def link(target: str, link_to: str) -> None:
    """
    Create a link to a target file or a folder.

    For the sake of simplicity, both target and link_to must be absolute path and must
    include the filename of the file or folder.
    Also do not include any trailing slash.

    e.g. link('/path/to/file', '/path/to/link')

    But not: link('/path/to/file', 'path/to/')
    or link('/path/to/folder/', '/path/to/link')

    Args:
        target (str): file or folder the link will point to
        link_to (str): Link to create
    """
    assert isinstance(target, str)
    assert Path(target).exists()
    assert isinstance(link_to, str)

    # Create the path to the link if it does not exist
    abs_path = Path(link_to).resolve().parent
    if not abs_path.is_dir():
        abs_path.mkdir(parents=True, exist_ok=True)

    # Make sure the file or folder recursively has the good mode
    chmod(target)

    # Create the link to target
    os.symlink(target, link_to)


def chmod(target: str) -> None:
    """
    Recursively set the chmod for files to 0600 and 0700 for folders.

    It's ok unless we need something more specific.

    Args:
        target (str): Root file or folder
    """
    assert isinstance(target, str)
    assert Path(target).exists()

    file_mode = stat.S_IRUSR | stat.S_IWUSR
    folder_mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR

    # Remove the immutable attribute recursively if there is one
    remove_immutable_attribute(target)

    if Path(target).is_file():
        Path(target).chmod(file_mode)

    elif Path(target).is_dir():
        # chmod the root item
        Path(target).chmod(folder_mode)

        # chmod recursively in the folder it it's one
        for root, dirs, files in os.walk(target):
            for cur_dir in dirs:
                (Path(root) / cur_dir).chmod(folder_mode)
            for cur_file in files:
                (Path(root) / cur_file).chmod(file_mode)

    else:
        msg = f"Unsupported file type: {target}"
        raise ValueError(msg)


def error(message: str) -> None:
    """
    Throw an error with the given message and immediately quit.

    Args:
        message(str): The message to display.
    """
    fail = "\033[91m"
    end = "\033[0m"
    sys.exit(fail + f"Error: {message}" + end)


def get_dropbox_folder_location() -> str:
    """
    Try to locate the Dropbox folder.

    Returns:
        (str) Full path to the current Dropbox folder
    """
    host_db_path = Path(os.environ["HOME"]) / ".dropbox" / "host.db"
    data = {}
    try:
        with host_db_path.open("r") as f_hostdb:
            data = f_hostdb.read().split()
    except OSError:
        error(constants.ERROR_UNABLE_TO_FIND_STORAGE.format(provider="Dropbox install"))
    return base64.b64decode(data[1]).decode()


def get_google_drive_folder_location() -> str | None:  # sourcery skip: extract-method
    """
    Try to locate the Google Drive folder.

    Returns:
        (str) Full path to the current Google Drive folder
    """
    gdrive_db_path = "Library/Application Support/Google/Drive/sync_config.db"
    yosemite_gdrive_db_path = "Library/Application Support/Google/Drive/user_default/sync_config.db"
    yosemite_gdrive_db = str(Path(os.environ["HOME"]) / yosemite_gdrive_db_path)
    if Path(yosemite_gdrive_db).is_file():
        gdrive_db_path = yosemite_gdrive_db

    googledrive_home = None

    gdrive_db = str(Path(os.environ["HOME"]) / gdrive_db_path)
    if Path(gdrive_db).is_file():
        con = sqlite3.connect(gdrive_db)
        if con:
            cur = con.cursor()
            query = "SELECT data_value FROM data WHERE entry_key = 'local_sync_root_path';"
            cur.execute(query)
            data = cur.fetchone()
            googledrive_home = str(data[0])
            con.close()

    if not googledrive_home:
        error(
            constants.ERROR_UNABLE_TO_FIND_STORAGE.format(
                provider="Google Drive install",
            ),
        )

    return googledrive_home


def get_icloud_folder_location() -> str:
    """
    Try to locate the iCloud Drive folder.

    Returns:
        (str) Full path to the iCloud Drive folder.
    """
    yosemite_icloud_path = "~/Library/Mobile Documents/com~apple~CloudDocs/"

    icloud_home = Path(yosemite_icloud_path).expanduser()

    if not icloud_home.is_dir():
        error(constants.ERROR_UNABLE_TO_FIND_STORAGE.format(provider="iCloud Drive"))

    return str(icloud_home)


def is_process_running(process_name: str) -> bool:
    """
    Check if a process with the given name is running.

    Args:
        (str): Process name, e.g. "Sublime Text"

    Returns:
        (bool): True if the process is running
    """
    is_running = False

    # On systems with pgrep, check if the given process is running
    if (Path("/usr") / "bin" / "pgrep").is_file():
        with Path(os.devnull).open("wb") as dev_null:
            returncode = subprocess.call(
                ["/usr/bin/pgrep", process_name],  # noqa: S603
                stdout=dev_null,
            )
        is_running = returncode == 0

    return is_running


def remove_acl(path: str) -> None:
    """
    Remove the ACL of the file or folder located on the given path.

    Also remove the ACL of any file and folder below the given one,
    recursively.

    Args:
        path (str): Path to the file or folder to remove the ACL for,
                    recursively.
    """
    # Some files have ACLs, let's remove them recursively
    if platform.system() == constants.PLATFORM_DARWIN and (Path("/bin") / "chmod").is_file():
        subprocess.call(["/bin/chmod", "-R", "-N", path])  # noqa: S603
    elif (platform.system() == constants.PLATFORM_LINUX) and (Path("/bin") / "setfacl").is_file():
        subprocess.call(["/bin/setfacl", "-R", "-b", path])  # noqa: S603


def remove_immutable_attribute(path: str) -> None:
    """
    Remove the immutable attribute of the given path.

    Remove the immutable attribute of the file or folder located on the given
    path. Also remove the immutable attribute of any file and folder below the
    given one, recursively.

    Args:
        path (str): Path to the file or folder to remove the immutable
                    attribute for, recursively.
    """
    # Some files have ACLs, let's remove them recursively
    if (platform.system() == constants.PLATFORM_DARWIN) and (Path("/usr") / "bin" / "chflags").is_file():
        subprocess.call(["/usr/bin/chflags", "-R", "nouchg", path])  # noqa: S603
    elif platform.system() == constants.PLATFORM_LINUX and (Path("/usr") / "bin" / "chattr").is_file():
        subprocess.call(["/usr/bin/chattr", "-R", "-f", "-i", path])  # noqa: S603


def can_file_be_synced_on_current_platform(path: str) -> bool:
    """
    Check if the given path can be synced locally.

    Check if it makes sense to sync the file at the given path on the current
    platform.
    For now we don't sync any file in the ~/Library folder on GNU/Linux.
    There might be other exceptions in the future.

    Args:
        (str): Path to the file or folder to check. If relative, prepend it
               with the home folder.
               'abc' becomes '~/abc'
               '/def' stays '/def'

    Returns:
        (bool): True if given file can be synced
    """
    # If the given path is relative, prepend home
    fullpath = str(Path(os.environ["HOME"]) / path)

    # Compute the ~/Library path on macOS
    # End it with a slash because we are looking for this specific folder and
    # not any file/folder named LibrarySomething
    library_path = str(Path(os.environ["HOME"]) / "Library")

    return platform.system() != constants.PLATFORM_LINUX or not fullpath.startswith(
        library_path,
    )
