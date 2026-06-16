import logging
from config import ATTRIBUTE_HEADERS, POSITION_ATTRIBUTE_COUNT

logger = logging.getLogger(__name__)

class Recruit:
    """Data class to hold recruit information."""
    def __init__(self, name, position, archetype, star_rating, gem_status, height, weight, recruit_class, hometown, attributes, dev_trait=""):
        self.name = name
        self.position = position
        self.archetype = archetype
        self.star_rating = star_rating
        self.gem_status = gem_status
        self.height = height
        self.weight = weight
        self.recruit_class = recruit_class
        self.hometown = hometown
        self.attributes = attributes
        self.dev_trait = dev_trait

    def is_valid(self) -> bool:
        """Validate none of the fields for the recruit are empty."""
        missing_fields = []
        for key, value in self.__dict__.items():
            if key not in ("attributes", "dev_trait") and (value == "Error" or value == ""):
                missing_fields.append(key)

        if len(missing_fields) > 0:
            list_str = ", ".join(map(str, missing_fields))
            logger.error(f"❌ Basic Info Validation Failed: Missing {list_str}")
            return False
        
        expected = POSITION_ATTRIBUTE_COUNT.get(self.position, 10)
        if len(self.attributes) != expected:
            logger.error(f"❌ Attributes Validation Failed: Found {len(self.attributes)}/{expected} attributes for {self.name}.")
            return False
        
        return True

    def to_row(self) -> list:
        """Converts recruit data into a row matching the ATTRIBUTE_HEADERS order."""
        # 1. Basic Info Columns
        row = [
            self.name,
            self.position,
            self.archetype,
            self.star_rating,
            self.gem_status,
            self.height,
            self.weight,
            self.recruit_class,
            self.hometown,
            self.dev_trait,
        ]

        # 2. Dynamic Attribute Columns
        # We look through ALL possible headers. If the recruit has it, we add the value.
        # If not, we add an empty string "".
        for header in ATTRIBUTE_HEADERS:
            # We standardize keys: "Short Accuracy" (sheet) -> "SHORT ACCURACY" (dict)
            key = header.upper()
            val = self.attributes.get(key, "")
            row.append(val)
            
        return row