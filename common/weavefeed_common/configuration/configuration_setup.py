import enum
import typing
from dataclasses import dataclass


class ConfigItemDataType(enum.Enum):
    """ Enumeration for configuration item data type """
    BOOLEAN = "bool"
    FLOAT = "float"
    INT = "int"
    STRING = "string"
    UNSIGNED_INT = "uint"


@dataclass(frozen=True)
class ConfigurationSetupItem:
    """ Configuration layout class """

    item_name: str
    item_type: ConfigItemDataType
    valid_values: typing.Optional[list] = None
    is_required: bool = False
    default_value: typing.Optional[object] = None


class ConfigurationSetup:
    """
    Class that defines the configuration format.

    This class holds the configuration layout by section, where each section
    contains a list of `ConfigurationSetupItem` instances describing individual
    configuration keys.
    """

    def __init__(self, setup_items: dict) -> None:
        """
        Initialize the ConfigurationSetup.

        Args:
            setup_items: A dictionary mapping section names (str) to lists of
                         ConfigurationSetupItem instances that define expected
                         config items.
        """
        if not isinstance(setup_items, dict):
            raise TypeError("setup_items must be a dict[str, "
                            "list[ConfigurationSetupItem]]")

        self._items = setup_items

    def get_sections(self) -> list:
        """
        Get a list of sections available.

        Returns:
            List of strings that represent the sections available.
        """
        return list(self._items.keys())

    def get_section(self, name: str) -> list[ConfigurationSetupItem]:
        """
        Get the list of configuration items for a given section.

        Args:
            name: The name of the section to retrieve items for.

        Returns:
            A list of ConfigurationSetupItem instances for the section.
            Returns an empty list if the section is not found.
        """
        return self._items.get(name, [])
