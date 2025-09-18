import configparser
import os
import typing
from shared.configuration.configuration_setup import (ConfigItemDataType,
                                                      ConfigurationSetup,
                                                      ConfigurationSetupItem)


class Configuration:
    """
    Class that wraps the functionality of configparser to support additional
    features such as trying multiple sources for the configuration item.
    """

    def __init__(self):
        """ Constructor for the configuration class. """

        self._parser = configparser.ConfigParser()
        self._config_file: typing.Optional[str] = None
        self._has_config_file: bool = False
        self._config_file_required: bool = False
        self._layout: typing.Optional[ConfigurationSetup] = None
        self._config_items: dict[str, dict[str, typing.Any]] = {}

        # Dispatch map: item type → handler function
        self._readers: dict[ConfigItemDataType,
                            typing.Callable[[str, ConfigurationSetupItem],
                                            typing.Any]] = {
            ConfigItemDataType.INT: self._read_int,
            ConfigItemDataType.STRING: self._read_str,
            ConfigItemDataType.BOOLEAN: self._read_bool,
            ConfigItemDataType.FLOAT: self._read_float,
            ConfigItemDataType.UNSIGNED_INT: self._read_uint,
        }

    def configure(self,
                  layout: ConfigurationSetup,
                  config_file: typing.Optional[str] = None,
                  file_required: bool = False) -> None:
        """
        Configure the parser with schema and optional file.

        Args:
            layout: Schema definition of configuration (required).
            config_file: Path to config file (optional).
            file_required: Whether file must exist and be readable.
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
            raise RuntimeError("Configuration layout must be set before "
                               "processing.")

        if self._config_file:
            try:
                files_read = self._parser.read(self._config_file)
            except configparser.ParsingError as ex:
                raise ValueError(
                    f"[ConfigError] Failed to parse file '{self._config_file}'"
                    f": {ex}") from ex

            if not files_read and self._config_file_required:
                raise ValueError(
                    f"[ConfigError] Required config file '{self._config_file}'"
                    "could not be opened."
                )

            self._has_config_file = bool(files_read)

        self._read_configuration()

    def get_entry(self, section: str, item: str) -> object:
        """
        Get a parsed configuration value.

        Args:
            section: Section name
            item: Config item name

        Returns:
            Parsed value (type depends on schema).

        Raises:
            ValueError: If section or item not found.
        """

        try:
            return self._config_items[section][item]
        except KeyError:
            raise ValueError(f"[ConfigError] Invalid key '{section}::{item}'")

    # -------------------------
    # Internal helpers
    # -------------------------

    def _lookup_value(
            self,
            section: str,
            item: ConfigurationSetupItem,
            file_getter: typing.Callable[[str, str], typing.Any]) -> typing.Any:
        """
        Get value from environment or config file.
        Env var format: SECTION_ITEM (uppercased).
        """
        env_var = f"{section}_{item.item_name}".upper()
        value = os.getenv(env_var)

        if value is None and self._has_config_file:
            try:
                value = file_getter(section, item.item_name)
            except (configparser.NoOptionError, configparser.NoSectionError):
                value = None

        return value if value is not None else item.default_value

    def _ensure_required(self,
                         section: str,
                         item: ConfigurationSetupItem,
                         value: typing.Any) -> typing.Any:
        if value is None and item.is_required:
            raise ValueError(f"[ConfigError] Missing required '{section}::"
                             f"{item.item_name}'")
        return value

    # -------------------------
    # Type readers
    # -------------------------

    def _read_str(self,
                  section: str,
                  item: ConfigurationSetupItem) -> str:
        value = self._lookup_value(section, item, self._parser.get)
        value = self._ensure_required(section, item, value)

        if value is None:
            return value

        if item.valid_values and value not in item.valid_values:
            raise ValueError(
                f"[ConfigError] '{section}::{item.item_name}' has invalid value '{value}', "
                f"expected one of {item.valid_values}"
            )
        return str(value)

    def _read_int(self,
                  section: str,
                  item: ConfigurationSetupItem) -> typing.Optional[int]:
        value = self._lookup_value(section, item, self._parser.getint)
        value = self._ensure_required(section, item, value)

        if value is None:
            return None

        try:
            return int(value)
        except (ValueError, TypeError) as ex:
            raise ValueError(
                f"[ConfigError] '{section}::{item.item_name}' has invalid "
                f"int '{value}'"
            ) from ex

    def _read_bool(self,
                   section: str,
                   item: ConfigurationSetupItem) -> typing.Optional[bool]:
        value = self._lookup_value(section, item, self._parser.getboolean)
        value = self._ensure_required(section, item, value)

        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "on"}:
                return True
            if lowered in {"false", "0", "no", "off"}:
                return False

        raise ValueError(
            f"[ConfigError] '{section}::{item.item_name}' has invalid boolean "
            f"'{value}'"
        )

    def _read_float(self,
                    section: str,
                    item: ConfigurationSetupItem) -> typing.Optional[float]:
        value = self._lookup_value(section, item, self._parser.getfloat)
        value = self._ensure_required(section, item, value)

        if value is None:
            return None

        try:
            return float(value)
        except (ValueError, TypeError) as ex:
            raise ValueError(
                f"[ConfigError] '{section}::{item.item_name}' has invalid "
                f"float '{value}'"
            ) from ex

    def _read_uint(self,
                   section: str,
                   item: ConfigurationSetupItem) -> typing.Optional[int]:
        value = self._read_int(section, item)
        if value is None:
            return None
        if value < 0:
            raise ValueError(
                f"[ConfigError] '{section}::{item.item_name}' has invalid "
                f"unsigned int '{value}'"
            )
        return value

    # -------------------------
    # Main schema processor
    # -------------------------

    def _read_configuration(self) -> None:
        for section_name in self._layout.get_sections():
            section_items = self._layout.get_section(section_name)

            for section_item in section_items:
                reader = self._readers.get(section_item.item_type)
                if not reader:
                    raise ValueError(
                        f"[ConfigError] Unsupported type "
                        f"'{section_item.item_type}' "
                        f"for '{section_name}::{section_item.item_name}'"
                    )

                value = reader(section_name, section_item)

                if section_name not in self._config_items:
                    self._config_items[section_name] = {}
                self._config_items[section_name][section_item.item_name] = value
