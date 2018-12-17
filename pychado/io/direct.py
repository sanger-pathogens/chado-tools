import sqlalchemy.sql
from . import iobase
from ..orm import organism


class DirectIOClient(iobase.IOClient):
    """Class for inserting, updating or deleting database entries"""

    def select_organisms(self, public_only: bool, query_version: bool) -> sqlalchemy.sql.Select:
        """Loads organisms from the database"""
        if public_only:
            public_type_term = self._load_cvterm("genedb_public")
            query = self.query_organisms_by_property_type(public_type_term.cvterm_id, query_version)
        else:
            query = self.query_all_organisms(query_version)
        return query.statement

    def insert_organism(self, genus: str, species: str, abbreviation: str, common_name=None,
                        infraspecific_name=None, comment=None, genome_version=None):
        """Inserts an organism into the database"""
        genus_species_entry = self.session.query(organism.Organism).filter_by(
            genus=genus, species=species, infraspecific_name=infraspecific_name).first()
        abbreviation_entry = self.session.query(organism.Organism).filter_by(abbreviation=abbreviation).first()
        if genus_species_entry:
            print("An organism with genus '" + genus + "', species '" + species
                  + "' and strain '" + infraspecific_name + "' is already present in the database.")
        elif abbreviation_entry:
            print("An organism with abbreviation '" + abbreviation + "' is already present in the database.")
        else:
            organism_entry = organism.Organism(genus=genus, species=species, abbreviation=abbreviation,
                                               common_name=common_name, infraspecific_name=infraspecific_name,
                                               comment=comment, version=genome_version)
            self.session.add(organism_entry)
            self.session.commit()
            print("An organism with genus '" + genus + "' and species '" + species
                  + "' has been inserted into the database.")

    def delete_organism(self, abbreviation: str):
        """Deletes an organism from the database"""
        obj = self.session.query(organism.Organism).filter_by(abbreviation=abbreviation).first()
        if not obj:
            print("An organism with abbreviation '" + abbreviation + "' is not present in the database.")
        else:
            self.session.delete(obj)
            self.session.commit()
            print("An organism with abbreviation '" + abbreviation + "' has been deleted from the database.")
