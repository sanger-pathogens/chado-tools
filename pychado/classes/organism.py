class Organism:
    """Class for organisms as used in the 'organism' CHADO table"""

    def __init__(self, identifier: int, abbreviation: str, genus: str, species: str, common_name: str, comment: str):
        """Initialize an organism"""
        self.id: int = identifier
        self.abbr: str = abbreviation
        self.genus: str = genus
        self.species: str = species
        self.common: str = common_name
        self.comment: str = comment
