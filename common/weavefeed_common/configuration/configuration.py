import configparser
import os
import typing
from shared.configuration.configuration_setup import ConfigItemDataType, \
                                                     ConfigurationSetup, \
                                                     ConfigurationSetupItem


class Configuration:
    """
    Class that wraps the functionality of configparser to support additional
    features such as trying multiple sources for the configuration item.
    """

    def __init__(self):
        """ Constructor for the configuration class. """

        self._parser = configparser.ConfigParser()

        self._config_file : str = ''
        self._has_config_file = False
        self._config_file_required = False
        self._layout : typing.Optional[ConfigurationSetup] = None
        self._config_items = {}

    def configure(self, layout: ConfigurationSetup,
                  config_file: str = None, file_required : bool = False):
        """
        Constructor for the configuration base class, it take in a layout
        class to validate the file.

        Example of layout:
        {
            "logging": [
                ConfigurationSetupItem(
                    "log_level", ConfigItemDataType.STRING,
                    valid_values=['DEBUG', 'INFO'],
                    default_value="INFO")
            ]
        }

        parameters:
            layout : Dictionary defining the configuration file
            config_file : Config file to read (optional, default = None)
            file_required : Is the file required (optional, default = False)
            required_files : Dict of required item (optional, default = None)
        """
        if layout is None:
            raise ValueError("Configuration layout cannot be None.")

        self._config_file = config_file
        self._config_file_required = file_required
        self._layout = layout

    def process_config(self):
        """
        Process the configuration
        """

        if self._layout is None:
            raise RuntimeError("Configuration layout must be set before processing.")

        if self._config_file:
            try:
                files_read = self._parser.read(self._config_file)

            except configparser.ParsingError as ex:
                raise ValueError(
                    f"Failed to read required config file, reason: {ex}") from ex

            if not files_read and self._config_file_required:
                raise ValueError(
                    f"Failed to open required config file '{self._config_file}'")

            if files_read:
                self._has_config_file = True

        self._read_configuration()

    def get_entry(self, section : str, item : str) -> object:
        """
        Get a configuration entry item value from a section.

        parameters:
            section (str) : Name of section
            item (str) : Name of configuration item to retrieve

        returns:
            Value of entry, the type depends on the items type - e.g.
            string (str) or integer (int).
        """

        if section not in self._config_items:
            raise ValueError(f"Invalid section '{section}'")

        if item not in self._config_items[section]:
            raise ValueError(f"Invalid config item {section}::{item}'")

        return self._config_items[section][item]

    def _read_configuration(self):

        sections = self._layout.get_sections()

        for section_name in sections:
            section_items = self._layout.get_section(section_name)

            for section_item in section_items:

                if section_item.item_type == ConfigItemDataType.INT:
                    item_value : int = self._read_int(section_name, section_item)

                elif section_item.item_type == ConfigItemDataType.STRING:
                    item_value: str = self._read_str(section_name,
                                                     section_item.item_name,
                                                     section_item)

                elif section_item.item_type == ConfigItemDataType.BOOLEAN:
                    item_value: bool = self._read_bool(section_name,
                                                       section_item)

                elif section_item.item_type == ConfigItemDataType.FLOAT:
                    item_value: float = self._read_float(section_name,
                                                         section_item)

                elif section_item.item_type == ConfigItemDataType.UNSIGNED_INT:
                    item_value: int = self._read_uint(section_name,
                                                      section_item)

                else:
                    raise ValueError(
                        f"Unsupported config item type '{section_item.item_type}' "
                        f"for item '{section_item.item_name}' in section "
                        f"'{section_name}'"
                    )

                if section_name not in self._config_items:
                    self._config_items[section_name] = {}

                self._config_items[section_name][section_item.item_name] = item_value

    def _read_str(self, section: str, option: str, fmt: ConfigurationSetupItem) -> str:
        """
        Read a configuration option of type str. Checks env var first, then config file.
        If valid_values is set, ensures the result is one of them.

        Returns:
            str value or raises ValueError if missing/invalid and required.
        """
        env_variable: str = f"{section}_{option}".upper()
        value = os.getenv(env_variable)

        if value is None and self._has_config_file:
            try:
                value = self._parser.get(section, option)
            except (configparser.NoOptionError, configparser.NoSectionError):
                value = None

        value = value if value else fmt.default_value

        if value is None and fmt.is_required:
            raise ValueError(f"Missing required config option '{section}::{fmt.item_name}'")

        if fmt.valid_values and value not in fmt.valid_values:
            raise ValueError(
                f"Invalid value '{value}' for '{section}::{fmt.item_name}'. "
                f"Expected one of {fmt.valid_values}."
            )

        return value

    def _read_int(self, section: str, fmt: ConfigurationSetupItem) -> int:
        """
        Read a configuration option of type int. Checks env var first, then
        config file.

        Returns:
            int value or raises ValueError if missing/invalid and required.
        """
        env_variable: str = f"{section}_{fmt.item_name}".upper()
        value = os.getenv(env_variable)

        if value is None and self._has_config_file:
            try:
                value = self._parser.getint(section, fmt.item_name)
            except (configparser.NoOptionError, configparser.NoSectionError):
                value = None
            except ValueError as ex:
                raise ValueError(
                    f"Config file option '{fmt.item_name}' is not a valid int."
                ) from ex

        value = value if value is not None else fmt.default_value

        if value is None and fmt.is_required:
            raise ValueError(
                f"Missing required config option '{section}::{fmt.item_name}'")

        try:
            return int(value)
        except (ValueError, TypeError) as ex:
            raise ValueError(
                f"Configuration option '{fmt.item_name}' with value '{value}' is not a valid int."
            ) from ex

    def _read_bool(self, section: str, fmt: ConfigurationSetupItem) -> bool:
        """
        Read a configuration option of type bool. Checks env var first, then config file.
        Accepts common string bool values (true/false, yes/no, 1/0).
        Returns:
            bool value or raises ValueError if invalid and required.
        """
        env_variable: str = f"{section}_{fmt.item_name}".upper()
        value = os.getenv(env_variable)

        if value is None and self._has_config_file:
            try:
                value = self._parser.getboolean(section, fmt.item_name)
            except (configparser.NoOptionError, configparser.NoSectionError):
                value = None
            except ValueError as ex:
                raise ValueError(
                    f"Config file option '{fmt.item_name}' is not a valid boolean."
                ) from ex

        value = value if value is not None else fmt.default_value

        if value is None and fmt.is_required:
            raise ValueError(f"Missing required config option '{section}::{fmt.item_name}'")

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ["true", "1", "yes", "on"]:
                return True

            if lowered in ["false", "0", "no", "off"]:
                return False

        raise ValueError(
            f"Configuration option '{fmt.item_name}' with value '{value}' is not a valid boolean."
        )

    def _read_float(self, section: str, fmt: ConfigurationSetupItem) -> float:
        """
        Read a configuration option of type float. It checks for an environment
        variable first (format is SECTION_OPTION), then the configuration file
        if it exists. If missing and required, or invalid, raises ValueError.

        Parameters:
            section : Configuration section name
            fmt     : ConfigurationSetupItem containing item_name,
                      default_value, and is_required

        Returns:
            float value of the configuration option

        Raises:
            ValueError if the value is required and missing, or not a valid
            float
        """
        env_variable: str = f"{section}_{fmt.item_name}".upper()
        value = os.getenv(env_variable)

        # If no env var, check config file if it exists
        if value is None and self._has_config_file:
            try:
                value = self._parser.getfloat(section, fmt.item_name)
            except (configparser.NoOptionError, configparser.NoSectionError):
                value = None
            except ValueError as ex:
                raise ValueError(
                    f"Config file option '{fmt.item_name}' is not a valid float."
                ) from ex

        # Use default if still not set
        value = value if value is not None else fmt.default_value

        if value is None and fmt.is_required:
            raise ValueError(
                f"Missing required config option '{section}::{fmt.item_name}'"
            )

        # If already a float (e.g. from getfloat), return it
        if isinstance(value, float):
            return value

        # If it's a string, try to convert to float
        try:
            return float(value)
        except (ValueError, TypeError) as ex:
            raise ValueError(
                f"Configuration option '{fmt.item_name}' with value '{value}' is not a valid float."
            ) from ex

    def _read_uint(self, section : str,
                   fmt : ConfigurationSetupItem) -> int:
        """
        Read a configuration option of type int, firstly it will check for
        an environment variable (format is section_option), otherwise try the
        configuration file (if it exists). An ValueError exception is thrown
        it's missing and marked as is_required or is not an unsigned int.

        parameters:
            section : Configuration section
            option : Configuration option to read
            default : Default value (if not a required variable)
            is_required : Is a required env variable flag (default is False)

        returns:
            An unsigned int or None if it's not a required field.
        """
        value : int = self._read_int(section, fmt)

        if value is None:
            return value

        if value < 0:
            raise ValueError((f"Configuration option '{fmt.item_name}' with a"
                              f" value of '{value}' is not an unsigned int."))

        return value
