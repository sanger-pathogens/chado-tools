from . import iobase
from .. import ddl
from ..orm import organism


class DirectIOClient(iobase.IOClient):
    """Class for inserting, updating or deleting database entries"""

    def insert_organism(self, genus: str, species: str, abbreviation: str, common_name=None,
                        infraspecific_name=None, comment=None):
        """Inserts an organism into the database"""
        obj = self.session.query(organism.Organism).filter_by(genus=genus, species=species).first()
        if obj:
            print("An organism with genus '" + genus + "' and species '" + species
                  + "' is already present in the database.")
        else:
            obj = organism.Organism(genus=genus, species=species, abbreviation=abbreviation, common_name=common_name,
                                    infraspecific_name=infraspecific_name, comment=comment)
            self.session.add(obj)
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


class DirectIOSetupClient(ddl.SchemaSetupClient, DirectIOClient):
    """Base class for setting up a CHADO database schema AND read-write access"""
    pass
