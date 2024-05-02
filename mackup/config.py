"""Package used to manage the .mackup.cfg config file."""

import os
import os.path
from configparser import ConfigParser
from pathlib import Path

from mackup.constants import (
    CUSTOM_APPS_DIR,
    ENGINE_DROPBOX,
    ENGINE_FS,
    ENGINE_GDRIVE,
    ENGINE_ICLOUD,
    MACKUP_BACKUP_PATH,
    MACKUP_CONFIG_FILE,
)
from mackup.utils import (
    error,
    get_dropbox_folder_location,
    get_google_drive_folder_location,
    get_icloud_folder_location,
)

try:
    import configparser
except ImportError:
    import ConfigParser as configparser  # noqa: N813


class Config:
    """The Mackup Config class."""

    def __init__(self, filename: str | None = None) -> None:
        """
        Create a Config instance.

        Args:
            filename (str): Optional filename of the config file. If empty,
                            defaults to MACKUP_CONFIG_FILE
        """
        assert isinstance(filename, str) or filename is None

        # Initialize the parser
        self._parser = self._setup_parser(filename)

        # Do we have an old config file?
        self._warn_on_old_config()

        # Get the storage engine
        self._engine = self._parse_engine()

        # Get the path where the Mackup folder is
        self._path = self._parse_path()

        # Get the directory replacing 'Mackup', if any
        self._directory = self._parse_directory()

        # Get the list of apps to ignore
        self._apps_to_ignore = self._parse_apps_to_ignore()

        # Get the list of apps to allow
        self._apps_to_sync = self._parse_apps_to_sync()

    @property
    def engine(self) -> str:
        """
        The engine used by the storage.

        ENGINE_DROPBOX, ENGINE_GDRIVE, ENGINE_ICLOUD or ENGINE_FS.

        Returns:
            str
        """
        return str(self._engine)

    @property
    def path(self) -> str:
        """
        Path to the Mackup configuration files.

        The path to the directory where Mackup is gonna create and store his
        directory.

        Returns:
            str
        """
        return str(self._path)

    @property
    def directory(self) -> str:
        """
        The name of the Mackup directory, named Mackup by default.

        Returns:
            str
        """
        return str(self._directory)

    @property
    def fullpath(self) -> str:
        """
        Full path to the Mackup configuration files.

        The full path to the directory when Mackup is storing the configuration
        files.

        Returns:
            str
        """
        return str(Path(self.path) / self.directory)

    @property
    def apps_to_ignore(self) -> set:
        """
        Get the list of applications ignored in the config file.

        Returns:
            set. Set of application names to ignore, lowercase
        """
        return set(self._apps_to_ignore)

    @property
    def apps_to_sync(self) -> set:
        """
        Get the list of applications allowed in the config file.

        Returns:
            set. Set of application names to allow, lowercase
        """
        return set(self._apps_to_sync)

    def _setup_parser(self, filename: str | None = None) -> ConfigParser:  # noqa: PLR6301
        """
        Configure the ConfigParser instance the way we want it.

        Args:
            filename (str) or None

        Returns:
            ConfigParser
        """
        assert isinstance(filename, str) or filename is None

        # If we are not overriding the config filename
        if not filename:
            filename = MACKUP_CONFIG_FILE

        parser = configparser.ConfigParser(allow_no_value=True, inline_comment_prefixes=(";", "#"))
        parser.read(str(Path(os.environ["HOME"]) / filename))

        return parser

    def _warn_on_old_config(self) -> None:
        """Warn the user if an old config format is detected."""
        # Is an old section in the config file?
        old_sections = ["Allowed Applications", "Ignored Applications"]
        for old_section in old_sections:
            if self._parser.has_section(old_section):
                error(
                    (
                        "Old config file detected. Aborting.\n"
                        "\n"
                        "An old section (e.g. [Allowed Applications]"
                        " or [Ignored Applications] has been detected"
                        f" in your {MACKUP_CONFIG_FILE} file.\n"
                        "I'd rather do nothing than do something you"
                        " do not want me to do.\n"
                        "\n"
                        "Please read the up to date documentation on"
                        " <https://github.com/lra/mackup> and migrate"
                        " your configuration file."
                    ),
                )

    def _parse_engine(self) -> str:
        """
        Parse the storage engine in the config.

        Returns:
            str
        """
        if self._parser.has_option("storage", "engine"):
            engine = str(self._parser.get("storage", "engine"))
        else:
            engine = ENGINE_DROPBOX

        assert isinstance(engine, str)

        if engine not in {
            ENGINE_DROPBOX,
            ENGINE_GDRIVE,
            ENGINE_ICLOUD,
            ENGINE_FS,
        }:
            msg = f"Unknown storage engine: {engine}"
            raise ConfigError(msg)

        return str(engine)

    def _parse_path(self) -> str:
        """
        Parse the storage path in the config.

        Returns:
            str
        """
        path = ""
        if self.engine == ENGINE_DROPBOX:
            path = get_dropbox_folder_location()
        elif self.engine == ENGINE_GDRIVE:
            path = get_google_drive_folder_location()
        elif self.engine == ENGINE_ICLOUD:
            path = get_icloud_folder_location()
        elif self.engine == ENGINE_FS:
            if self._parser.has_option("storage", "path"):
                cfg_path = self._parser.get("storage", "path")
                path = Path(os.environ["HOME"]) / cfg_path
            else:
                msg = "The required 'path' can't be found while the 'file_system' engine is used."
                raise ConfigError(msg)

        return str(path)

    def _parse_directory(self) -> str:
        """
        Parse the storage directory in the config.

        Returns:
            str
        """
        if self._parser.has_option("storage", "directory"):
            directory = self._parser.get("storage", "directory")
            # Don't allow CUSTOM_APPS_DIR as a storage directory
            if directory == CUSTOM_APPS_DIR:
                msg = f"{CUSTOM_APPS_DIR} cannot be used as a storage directory."
                raise ConfigError(msg)
        else:
            directory = MACKUP_BACKUP_PATH

        return str(directory)

    def _parse_apps_to_ignore(self) -> set:
        """
        Parse the applications to ignore in the config.

        Returns:
            set
        """
        # Is the "[applications_to_ignore]" in the cfg file?
        section_title = "applications_to_ignore"
        return set(self._parser.options(section_title)) if self._parser.has_section(section_title) else set()

    def _parse_apps_to_sync(self) -> set:
        """
        Parse the applications to backup in the config.

        Returns:
            set
        """
        # Is the "[applications_to_sync]" section in the cfg file?
        section_title = "applications_to_sync"
        return set(self._parser.options(section_title)) if self._parser.has_section(section_title) else set()


class ConfigError(Exception):
    """Exception used for handle errors in the configuration."""
