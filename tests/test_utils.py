import os
import stat
import tempfile
import unittest
from pathlib import Path

import pytest

# from unittest.mock import patch
from mackup import utils


def convert_to_octal(file_name):
    """Use os.stat; returns file permissions (read, write, execute) as an octal."""
    return oct(Path(file_name).stat()[stat.ST_MODE])[-3:]


class TestMackup(unittest.TestCase):
    def test_confirm_yes(self):
        # Override the input used in utils
        def custom_input(_):
            return "Yes"

        utils.input = custom_input
        assert utils.confirm("Answer Yes to this question")

    def test_confirm_no(self):
        # Override the input used in utils
        def custom_input(_):
            return "No"

        utils.input = custom_input
        assert not utils.confirm("Answer No to this question")

    def test_confirm_typo(self):
        # Override the input used in utils
        def custom_input(_):
            return "No"

        utils.input = custom_input
        assert not utils.confirm("Answer garbage to this question")

    def test_delete_file(self):
        # Create a tmp file
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfpath = tfile.name
        tfile.close()

        # Make sure the created file exists
        assert Path(tfpath).is_file()

        # Check if mackup can really delete it
        utils.delete(tfpath)
        assert not Path(tfpath).exists()

    def test_delete_folder_recursively(self):
        # Create a tmp folder
        tfpath = tempfile.mkdtemp()

        # Let's put a file in it just for fun
        tfile = tempfile.NamedTemporaryFile(dir=tfpath, delete=False)
        filepath = tfile.name
        tfile.close()

        # Let's put another folder in it
        subfolder_path = tempfile.mkdtemp(dir=tfpath)

        # And a file in the subfolder
        tfile = tempfile.NamedTemporaryFile(dir=subfolder_path, delete=False)
        subfilepath = tfile.name
        tfile.close()

        # Make sure the created files and folders exists
        assert Path(tfpath).is_dir()
        assert Path(filepath).is_file()
        assert Path(subfolder_path).is_dir()
        assert Path(subfilepath).is_file()

        # Check if mackup can really delete it
        utils.delete(tfpath)
        assert not Path(tfpath).exists()
        assert not Path(filepath).exists()
        assert not Path(subfolder_path).exists()
        assert not Path(subfilepath).exists()

    def test_copy_file(self):  # sourcery skip: class-extract-method
        # Create a tmp file
        tfile = tempfile.NamedTemporaryFile(delete=False)
        srcfile = tfile.name
        tfile.close()

        # Create a tmp folder
        dstpath = tempfile.mkdtemp()
        # Set the destination filename
        dstfile = str(Path(dstpath) / "subfolder" / Path(srcfile).name)

        # Make sure the source file and destination folder exist and the
        # destination file doesn't yet exist
        assert Path(srcfile).is_file()
        assert Path(dstpath).is_dir()
        assert not Path(dstfile).exists()

        # Check if mackup can copy it
        utils.copy(srcfile, dstfile)
        assert Path(srcfile).is_file()
        assert Path(dstpath).is_dir()
        assert Path(dstfile).exists()

        # Let's clean up
        utils.delete(dstpath)

    def test_copy_fail(self):  # sourcery skip: extract-duplicate-method
        # Create a tmp FIFO file
        tfile = tempfile.NamedTemporaryFile()
        srcfile = tfile.name
        tfile.close()
        os.mkfifo(srcfile)

        # Create a tmp folder
        dstpath = tempfile.mkdtemp()
        # Set the destination filename
        dstfile = str(Path(dstpath) / "subfolder" / Path(srcfile).name)

        # Make sure the source file and destination folder exist and the
        # destination file doesn't yet exist
        assert not Path(srcfile).is_file()
        assert stat.S_ISFIFO(Path(srcfile).stat().st_mode)
        assert Path(dstpath).is_dir()
        assert not Path(dstfile).exists()

        # Check if mackup can copy it
        with pytest.raises(ValueError, match="function copy"):
            raise ValueError(utils.copy, srcfile, dstfile)
        assert not Path(srcfile).is_file()
        assert stat.S_ISFIFO(Path(srcfile).stat().st_mode)
        assert Path(dstpath).is_dir()
        assert not Path(dstfile).exists()

        # Let's clean up
        utils.delete(srcfile)
        utils.delete(dstpath)

    def test_copy_file_to_dir(self):  # sourcery skip: extract-duplicate-method
        """Copies a file to a destination folder that already exists."""
        # Create a tmp folder
        srcpath = tempfile.mkdtemp()

        # Create a tmp file
        tfile = tempfile.NamedTemporaryFile(delete=False, dir=srcpath)
        srcfile = tfile.name
        tfile.close()

        # Create a tmp folder
        dstpath = tempfile.mkdtemp()

        # Set the destination filename
        srcpath_basename = Path(srcpath).name
        dstfile = str(
            Path(dstpath) / "subfolder" / srcpath_basename / Path(srcfile).name,
        )
        # Make sure the source file and destination folder exist and the
        # destination file doesn't yet exist
        assert Path(srcpath).is_dir()
        assert Path(srcfile).is_file()
        assert Path(dstpath).is_dir()
        assert not Path(dstfile).exists()

        # Check if mackup can copy it
        utils.copy(srcfile, dstfile)
        assert Path(srcpath).is_dir()
        assert Path(srcfile).is_file()
        assert Path(dstpath).is_dir()
        assert Path(dstfile).exists()

        # Let's clean up
        utils.delete(srcpath)
        utils.delete(dstpath)

    def test_copy_dir(self):  # sourcery skip: extract-duplicate-method
        """Copies a directory recursively to the destination path."""
        # Create a tmp folder
        srcpath = tempfile.mkdtemp()

        # Create a tmp file
        tfile = tempfile.NamedTemporaryFile(delete=False, dir=srcpath)
        srcfile = tfile.name
        tfile.close()

        # Create a tmp folder
        dstpath = tempfile.mkdtemp()

        # Set the destination filename
        srcpath_basename = Path(srcpath).name
        dstfile = str(Path(dstpath) / srcpath_basename / Path(srcfile).name)
        # Make sure the source file and destination folder exist and the
        # destination file doesn't yet exist
        assert Path(srcpath).is_dir()
        assert Path(srcfile).is_file()
        assert Path(dstpath).is_dir()
        assert not Path(dstfile).exists()

        # Check if mackup can copy it
        utils.copy(srcpath, dstfile)
        assert Path(srcpath).is_dir()
        assert Path(srcfile).is_file()
        assert Path(dstpath).is_dir()
        assert Path(dstfile).exists()

        # Let's clean up
        utils.delete(srcpath)
        utils.delete(dstpath)

    def test_link_file(self):
        # Create a tmp file
        tfile = tempfile.NamedTemporaryFile(delete=False)
        srcfile = tfile.name
        tfile.close()

        # Create a tmp folder
        dstpath = tempfile.mkdtemp()
        # Set the destination filename
        dstfile = str(Path(dstpath) / "subfolder" / Path(srcfile).name)

        # Make sure the source file and destination folder exist and the
        # destination file doesn't yet exist
        assert Path(srcfile).is_file()
        assert Path(dstpath).is_dir()
        assert not Path(dstfile).exists()

        # Check if mackup can link it and the link points to the correct place
        utils.link(srcfile, dstfile)
        assert Path(srcfile).is_file()
        assert Path(dstpath).is_dir()
        assert Path(dstfile).exists()
        assert str(Path(dstfile).readlink()) == srcfile

        # Let's clean up
        utils.delete(dstpath)

    def test_chmod_file(self):
        # Create a tmp file
        tfile = tempfile.NamedTemporaryFile(delete=False)
        file_name = tfile.name

        # Create a tmp directory with a sub folder
        dir_name = tempfile.mkdtemp()
        nested_dir = tempfile.mkdtemp(dir=dir_name)

        # # File Tests

        # Change the tmp file stats to S_IWRITE (200), write access only
        Path(file_name).chmod(stat.S_IWRITE)
        assert convert_to_octal(file_name) == "200"

        # Check to make sure that utils.chmod changes the bits to 600,
        # which is read and write access for the owner
        utils.chmod(file_name)
        assert convert_to_octal(file_name) == "600"

        # # Directory Tests

        # Change the tmp folder stats to S_IREAD (400), read access only
        Path(dir_name).chmod(stat.S_IREAD)
        assert convert_to_octal(dir_name) == "400"

        # Check to make sure that utils.chmod changes the bits of all
        # directories to 700, which is read, write, and execute access for the
        # owner
        utils.chmod(dir_name)
        assert convert_to_octal(dir_name) == "700"
        assert convert_to_octal(nested_dir) == "700"

        # Use an "unsupported file type". In this case, /dev/null
        with pytest.raises(ValueError, match="/dev/null"):
            raise ValueError(utils.chmod, os.devnull)

    def test_error(self):
        test_string = "Hello World"
        with pytest.raises(SystemExit):
            raise SystemExit(utils.error, test_string)

    def test_failed_backup_location(self):
        """Tests for the error that should occur if the backup folder cannot be found for Dropbox and Google."""
        # Hack to make our home folder some temporary folder
        temp_home = tempfile.mkdtemp()
        utils.os.environ["HOME"] = temp_home

        # Check for the missing Dropbox folder
        assert not (Path(temp_home) / ".dropbox" / "host.db").exists()
        with pytest.raises(SystemExit):
            raise SystemExit(utils.get_dropbox_folder_location)

        # Check for the missing Google Drive folder
        assert not (
            Path(temp_home) / "Library" / "Application Support" / "Google" / "Drive" / "sync_config.db"
        ).exists()
        with pytest.raises(SystemExit):
            raise SystemExit(utils.get_google_drive_folder_location)

    def test_is_process_running(self):
        # A pgrep that has one letter and a wildcard will always return id 1
        assert utils.is_process_running("a*")
        assert not utils.is_process_running("some imaginary process")

    def test_can_file_be_synced_on_current_platform(self):
        # Any file path will do, even if it doesn't exist
        path = "some/file"

        # Force the Mac OSX Test using lambda magic
        utils.platform.system = lambda *args: utils.constants.PLATFORM_DARWIN  # noqa: ARG005
        assert utils.can_file_be_synced_on_current_platform(path)

        # Force the Linux Test using lambda magic
        utils.platform.system = lambda *args: utils.constants.PLATFORM_LINUX  # noqa: ARG005
        assert utils.can_file_be_synced_on_current_platform(path)

        # Try to use the library path on Linux, which shouldn't work
        path = str(Path(os.environ["HOME"]) / "Library")
        assert not utils.can_file_be_synced_on_current_platform(path)
