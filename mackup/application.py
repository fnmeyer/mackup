"""
Application Profile.

An Application Profile contains all the information about an application in
Mackup. Name, files, ...
"""

import os
from pathlib import Path

from mackup import utils
from mackup.mackup import Mackup


class ApplicationProfile:
    """Instantiate this class with application specific data."""

    def __init__(
        self,
        mackup: Mackup,
        files: list,
        dry_run,  # noqa: ANN001
        verbose,  # noqa: ANN001
    ) -> None:
        """
        Create an ApplicationProfile instance.

        Args:
            mackup (Mackup)
            files (list)
        """
        assert isinstance(mackup, Mackup)
        assert isinstance(files, set)

        self.mackup = mackup
        self.files = list(files)
        self.dry_run = dry_run
        self.verbose = verbose

    def getFilepaths(self, filename: str) -> tuple[str, str]:  # noqa: N802
        """Get home and mackup filepaths for given file.

        Args:
            filename (str)

        Returns:
            home_filepath, mackup_filepath (str, str)
        """
        return (
            str(Path(os.environ["HOME"]) / filename),
            str(Path(self.mackup.mackup_folder) / filename),
        )

    def backup(self) -> None:  # noqa: PLR0912  # sourcery skip: extract-duplicate-method, low-code-quality
        """
        Backup the application config files.

        Algorithm:
            if exists home/file
              if home/file is a real file
                if exists mackup/file
                  are you sure?
                  if sure
                    rm mackup/file
                    mv home/file mackup/file
                    link mackup/file home/file
                else
                  mv home/file mackup/file
                  link mackup/file home/file
        """
        # For each file used by the application
        for filename in self.files:
            (home_filepath, mackup_filepath) = self.getFilepaths(filename)

            # If the file exists and is not already a link pointing to Mackup
            if Path(home_filepath).is_file() or (
                Path(home_filepath).is_dir()
                and not (
                    Path(home_filepath).is_symlink()
                    and (Path(mackup_filepath).is_file() or Path(mackup_filepath).is_dir())
                    and Path(home_filepath).samefile(mackup_filepath)
                )
            ):
                if self.verbose:
                    print(f"Backing up\n  {home_filepath}\n  to\n  {mackup_filepath} ...")
                else:
                    print(f"Backing up {filename} ...")

                if self.dry_run:
                    continue

                # Check if we already have a backup
                if Path(mackup_filepath).exists():
                    # Name it right
                    if Path(mackup_filepath).is_file():
                        file_type = "file"
                    elif Path(mackup_filepath).is_dir():
                        file_type = "folder"
                    elif Path(mackup_filepath).is_symlink():
                        file_type = "link"
                    else:
                        msg = f"Unsupported file: {mackup_filepath}"
                        raise ValueError(msg)

                    # Ask the user if he really wants to replace it
                    if utils.confirm(
                        (
                            f"A {file_type} named {mackup_filepath} already exists in the"
                            " backup.\nAre you sure that you want to"
                            " replace it?"
                        ),
                    ):
                        # Delete the file in Mackup
                        utils.delete(mackup_filepath)
                        # Copy the file
                        utils.copy(home_filepath, mackup_filepath)
                        # Delete the file in the home
                        utils.delete(home_filepath)
                        # Link the backuped file to its original place
                        utils.link(mackup_filepath, home_filepath)
                else:
                    # Copy the file
                    utils.copy(home_filepath, mackup_filepath)
                    # Delete the file in the home
                    utils.delete(home_filepath)
                    # Link the backuped file to its original place
                    utils.link(mackup_filepath, home_filepath)
            elif self.verbose:
                if Path(home_filepath).exists():
                    print(
                        f"Doing nothing\n  {home_filepath}\n  is already backed up to\n  {mackup_filepath}",
                    )
                elif Path(home_filepath).is_symlink():
                    print(f"Doing nothing\n  {home_filepath}\n  is a broken link, you might want to fix it.")
                else:
                    print(f"Doing nothing\n  {home_filepath}\n  does not exist")

    def restore(self) -> None:  # noqa: PLR0912
        # sourcery skip: low-code-quality
        """
        Restore the application config files.

        Algorithm:
            if exists mackup/file
              if exists home/file
                are you sure?
                if sure
                  rm home/file
                  link mackup/file home/file
              else
                link mackup/file home/file
        """
        # For each file used by the application
        for filename in self.files:
            (home_filepath, mackup_filepath) = self.getFilepaths(filename)

            # If the file exists and is not already pointing to the mackup file
            # and the folder makes sense on the current platform (Don't sync
            # any subfolder of ~/Library on GNU/Linux)
            file_or_dir_exists = Path(mackup_filepath).is_file() or Path(mackup_filepath).is_dir()
            pointing_to_mackup = (
                Path(home_filepath).is_symlink()
                and Path(mackup_filepath).exists()
                and Path(mackup_filepath).samefile(home_filepath)
            )
            supported = utils.can_file_be_synced_on_current_platform(filename)

            if file_or_dir_exists and not pointing_to_mackup and supported:
                if self.verbose:
                    print(f"Restoring\n  linking {home_filepath}\n  to      {mackup_filepath} ...")
                else:
                    print(f"Restoring {filename} ...")

                if self.dry_run:
                    continue

                # Check if there is already a file in the home folder
                if Path(home_filepath).exists():
                    # Name it right
                    if Path(home_filepath).is_file():
                        file_type = "file"
                    elif Path(home_filepath).is_dir():
                        file_type = "folder"
                    elif Path(home_filepath).is_symlink():
                        file_type = "link"
                    else:
                        msg = f"Unsupported file: {mackup_filepath}"
                        raise ValueError(msg)

                    if utils.confirm(
                        (
                            f"You already have a {file_type} named {filename} in your"
                            " home.\nDo you want to replace it with"
                            " your backup?"
                        ),
                    ):
                        utils.delete(home_filepath)
                        utils.link(mackup_filepath, home_filepath)
                else:
                    utils.link(mackup_filepath, home_filepath)
            elif self.verbose:
                if Path(home_filepath).exists():
                    print(f"Doing nothing\n  {mackup_filepath}\n  already linked by\n  {home_filepath}")
                elif Path(home_filepath).is_symlink():
                    print(f"Doing nothing\n  {home_filepath}\n  is a broken link, you might want to fix it.")
                else:
                    print(f"Doing nothing\n  {mackup_filepath}\n  does not exist")

    def uninstall(self) -> None:
        """
        Uninstall Mackup.

        Restore any file where it was before the 1st Mackup backup.

        Algorithm:
            for each file in config
                if mackup/file exists
                    if home/file exists
                        delete home/file
                    copy mackup/file home/file
            delete the mackup folder
            print how to delete mackup
        """
        # For each file used by the application
        for filename in self.files:
            (home_filepath, mackup_filepath) = self.getFilepaths(filename)

            # If the mackup file exists
            if Path(mackup_filepath).is_file() or Path(mackup_filepath).is_dir():
                # Check if there is a corresponding file in the home folder
                if Path(home_filepath).exists():
                    if self.verbose:
                        print(f"Reverting {mackup_filepath}\n  at {home_filepath} ...")
                    else:
                        print(f"Reverting {filename} ...")

                    if self.dry_run:
                        continue

                    # If there is, delete it as we are gonna copy the Dropbox
                    # one there
                    utils.delete(home_filepath)

                    # Copy the Dropbox file to the home folder
                    utils.copy(mackup_filepath, home_filepath)
            elif self.verbose:
                print(f"Doing nothing, {mackup_filepath} does not exist")
