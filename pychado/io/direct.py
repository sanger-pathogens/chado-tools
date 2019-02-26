from typing import List
from . import iobase, ontology
from .. import utils
from ..orm import organism, general


class DirectIOClient(iobase.ChadoClient):
    """Class for inserting, updating or deleting database entries"""

    def __init__(self, uri: str, verbose=False, test_environment=False):
        """Constructor"""

        # Connect to database
        self.test_environment = test_environment
        if self.test_environment:
            self.printer = utils.VerbosePrinter(verbose)
        else:
            super().__init__(uri, verbose)

    def __del__(self):
        """Destructor"""

        # Disconnect from database
        if not self.test_environment:
            super().__del__()

    def insert_organism(self, genus: str, species: str, abbreviation: str, common_name=None, infraspecific_name=None,
                        comment=None, genome_version=None, taxon_id=None, wikidata_id=None) -> None:
        """Inserts an organism and properties into the database"""

        # Insert organism
        organism_entry = self._handle_actual_organism(genus, species, infraspecific_name, abbreviation, common_name,
                                                      comment)

        # Insert properties
        self._handle_organism_properties(organism_entry, genome_version, taxon_id)

        # Insert database cross references
        self._handle_organism_cross_references(organism_entry, wikidata_id)

        # Commit changes
        self.session.commit()

    def delete_organism(self, abbreviation: str) -> None:
        """Deletes an organism from the database"""
        self._delete_organism(abbreviation)
        self.session.commit()

    def _handle_actual_organism(self, genus: str, species: str, infraspecific_name: str, abbreviation: str,
                                common_name: str, comment: str) -> organism.Organism:
        """Inserts or updates an entry in the 'organism' table and returns it"""
        if not common_name:
            common_name = abbreviation
        new_organism_entry = organism.Organism(genus=genus, species=species, abbreviation=abbreviation,
                                               common_name=common_name, infraspecific_name=infraspecific_name,
                                               comment=comment)
        organism_entry = self._handle_organism(new_organism_entry)
        return organism_entry

    def _handle_organism_properties(self, organism_entry: organism.Organism, genome_version: str, taxon_id: str
                                    ) -> List[organism.OrganismProp]:
        """Inserts and updates entries in the 'organismprop' table and returns them"""
        all_organismprop_entries = []

        if genome_version:
            # Insert/update entry for genome version
            version_cvterm = self._load_cvterm("version")
            new_organismprop_entry = organism.OrganismProp(organism_id=organism_entry.organism_id,
                                                           type_id=version_cvterm.cvterm_id, value=genome_version)
            organismprop_entry = self._handle_organismprop(new_organismprop_entry, organism_entry.abbreviation,
                                                           version_cvterm.name)
            all_organismprop_entries.append(organismprop_entry)

        if taxon_id:
            # Insert/update entry for NCBI taxon ID
            taxon_id_cvterm = self._load_cvterm("taxonId")
            new_organismprop_entry = organism.OrganismProp(organism_id=organism_entry.organism_id,
                                                           type_id=taxon_id_cvterm.cvterm_id, value=taxon_id)
            organismprop_entry = self._handle_organismprop(new_organismprop_entry, organism_entry.abbreviation,
                                                           taxon_id_cvterm.name)
            all_organismprop_entries.append(organismprop_entry)

        return all_organismprop_entries

    def _handle_organism_cross_references(self, organism_entry: organism.Organism, wikidata_id: str
                                          ) -> List[organism.OrganismDbxRef]:
        """Inserts and updates entries in the 'organism_dbxref' table and returns them"""
        all_organism_dbxref_entries = []
        if wikidata_id:

            # Get entry from 'db' table
            wikidata_db = self._load_db("Wikidata")
            wikidata_dbxref = ontology.create_dbxref(wikidata_db.name, wikidata_id)

            # Insert/update entry in the 'dbxref' table
            new_dbxref_entry = general.DbxRef(db_id=wikidata_db.db_id, accession=wikidata_id)
            dbxref_entry = self._handle_dbxref(new_dbxref_entry, wikidata_db.name)

            # Insert/update entry in the 'organism_dbxref' table
            new_organism_dbxref_entry = organism.OrganismDbxRef(organism_id=organism_entry.organism_id,
                                                                dbxref_id=dbxref_entry.dbxref_id)
            organism_dbxref_entry = self._handle_organism_dbxref(new_organism_dbxref_entry,
                                                                 organism_entry.abbreviation, wikidata_dbxref)
            all_organism_dbxref_entries.append(organism_dbxref_entry)

        return all_organism_dbxref_entries
