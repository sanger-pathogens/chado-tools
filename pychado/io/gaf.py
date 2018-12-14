from typing import List, Dict, Union
from Bio.UniProt import GOA
from . import iobase, ontology
from ..orm import general, cv, organism, pub, sequence


class GAFImportClient(iobase.ImportClient):
    """Class for importing genomic data from GAF files into Chado"""

    def __init__(self, uri: str, verbose=False, test_environment=False):
        """Constructor"""

        # Connect to database
        self.test_environment = test_environment
        if not self.test_environment:
            super().__init__(uri, verbose)

        # Load essentials
        if not self.test_environment:
            self._load_essentials()

    def __del__(self):
        """Destructor - disconnect from database"""
        if not self.test_environment:
            super().__del__()

    def _load_essentials(self) -> None:
        """Loads essential database entries"""
        self._date_term = self._load_cvterm("date")
        self._evidence_term = self._load_cvterm("evidence")
        self._default_pub = self._load_pub("null")
        self._go_db = self._load_db("GO")

    def load(self, filename: str, organism_name: str):
        """Import data from a GAF file into a Chado database"""

        # Load dependencies
        default_organism = self._load_organism(organism_name)
        features_with_product = set()

        # Loop over all entries in the GAF file
        with open(filename) as f:
            for gaf_record in GOA.gafiterator(f):

                # Get the feature entry
                feature_entry = self._load_feature(gaf_record, default_organism)
                if not feature_entry:
                    continue

                # Update/insert a feature_cvterm entry for the gene product
                if feature_entry.uniquename not in features_with_product:
                    self._handle_product_term(gaf_record, feature_entry)
                    features_with_product.add(feature_entry.uniquename)

                # Update/insert a feature_cvterm entry for the ontology term
                feature_cvterm_entry = self._handle_ontology_term(gaf_record, feature_entry)
                if not feature_cvterm_entry:
                    continue

                # Update/insert feature_cvtermprop entries for date and evidence code
                self._handle_properties(gaf_record, feature_cvterm_entry)

                # Update/insert feature_cvterm_dbxref entries
                self._handle_crossrefs(gaf_record, feature_cvterm_entry)

                # Update/insert feature_cvterm_pub entries
                self._handle_publications(gaf_record, feature_cvterm_entry)

        # Commit changes
        self.session.commit()

    def _load_feature(self, gaf_record: dict, organism_entry: organism.Organism) -> Union[None, sequence.Feature]:
        """Loads a feature entry from the database"""
        feature_name = gaf_record["DB_Object_ID"].strip()
        if not feature_name:
            return None
        feature_entry = self.query_first(sequence.Feature, organism_id=organism_entry.organism_id,
                                         uniquename=feature_name)
        return feature_entry

    def _handle_ontology_term(self, gaf_record: dict, feature_entry: sequence.Feature
                              ) -> Union[None, sequence.FeatureCvTerm]:
        """Inserts or updates an entry in the 'feature_cvterm' table and returns it"""

        # Extract ontology identifier from the GAF record and split it into db, accession, version
        ontology_term = gaf_record["GO_ID"].strip()
        (db_authority, accession, version) = ontology.split_dbxref(ontology_term)
        publication = gaf_record["DB:Reference"][0].strip()

        # Get entry from 'db' table
        db_entry = self.query_first(general.Db, name=db_authority)
        if not db_entry:
            self.printer.print("WARNING: Ontology '" + db_authority + "' not present in database.")
            return None

        # Get entry from 'dbxref' table
        dbxref_entry = self.query_first(general.DbxRef, db_id=db_entry.db_id, accession=accession)
        if not dbxref_entry:
            self.printer.print("WARNING: Ontology term '" + ontology_term + "' not present in database.")
            return None

        # Get entry from 'cvterm' table
        cvterm_entry = self.query_first(cv.CvTerm, dbxref_id=dbxref_entry.dbxref_id)
        if not cvterm_entry:
            self.printer.print("WARNING: CV term for ontology term '" + ontology_term
                               + "' not present in database.")
            return None

        # Insert/update entry in the 'pub' table
        if publication:
            new_pub_entry = pub.Pub(uniquename=publication, type_id=self._default_pub.type_id)
            pub_entry = self._handle_pub(new_pub_entry)
        else:
            pub_entry = self._default_pub

        # Extract existing ontology terms for this feature from the database
        existing_feature_cvterms = self.query_feature_cvterm_by_ontology(
            feature_entry.feature_id, [db_entry.db_id]).all()

        # Insert/update entry in the 'feature_cvterm' table
        new_feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=feature_entry.feature_id,
                                                          cvterm_id=cvterm_entry.cvterm_id,
                                                          pub_id=pub_entry.pub_id,
                                                          is_not=("NOT" in gaf_record["Qualifier"]))
        feature_cvterm_entry = self._handle_feature_cvterm(new_feature_cvterm_entry, existing_feature_cvterms,
                                                           cvterm_entry.name, feature_entry.uniquename)
        return feature_cvterm_entry

    def _handle_product_term(self, gaf_record: dict, feature_entry: sequence.Feature
                             ) -> Union[None, sequence.FeatureCvTerm]:
        """Inserts or updates an entry in the 'feature_cvterm' table and returns it"""

        # Extract the product name from the GAF record
        product = gaf_record["DB_Object_Name"].strip()
        if not product:
            return None
        publication = gaf_record["DB:Reference"][0].strip()

        # Insert/update entry in the 'db' table
        new_db_entry = general.Db(name="PRODUCT")
        db_entry = self._handle_db(new_db_entry)

        # Insert/update entry in the 'dbxref' table
        new_dbxref_entry = general.DbxRef(db_id=db_entry.db_id, accession=product)
        dbxref_entry = self._handle_dbxref(new_dbxref_entry, db_entry.name)

        # Insert/update entry in the 'cv' table
        new_cv_entry = cv.Cv(name="genedb_products")
        cv_entry = self._handle_cv(new_cv_entry)

        # Insert/update entry in the 'cvterm' table
        new_cvterm_entry = cv.CvTerm(cv_id=cv_entry.cv_id, dbxref_id=dbxref_entry.dbxref_id, name=product)
        cvterm_entry = self._handle_cvterm(new_cvterm_entry, cv_entry.name)

        # Insert/update entry in the 'pub' table
        if publication:
            new_pub_entry = pub.Pub(uniquename=publication, type_id=self._default_pub.type_id)
            pub_entry = self._handle_pub(new_pub_entry)
        else:
            pub_entry = self._default_pub

        # Extract existing product terms for this feature from the database
        existing_feature_cvterms = self.query_feature_cvterm_by_ontology(
            feature_entry.feature_id, [db_entry.db_id]).all()

        # Insert/update entry in the 'feature_cvterm' table
        new_feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=feature_entry.feature_id,
                                                          cvterm_id=cvterm_entry.cvterm_id,
                                                          pub_id=pub_entry.pub_id)
        feature_cvterm_entry = self._handle_feature_cvterm(new_feature_cvterm_entry, existing_feature_cvterms,
                                                           cvterm_entry.name, feature_entry.uniquename)
        return feature_cvterm_entry

    def _handle_properties(self, gaf_record: dict, feature_cvterm_entry: sequence.FeatureCvTerm
                           ) -> List[sequence.FeatureCvTermProp]:
        """Inserts or updates entries in the 'feature_cvtermprop' table and returns them"""

        # Extract existing properties for this feature_cvterm from the database
        existing_feature_cvtermprops = self.query_all(sequence.FeatureCvTermProp,
                                                      feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id)

        # Insert/update entry for 'date'
        date = gaf_record["Date"].strip()
        new_feature_cvtermprop_entry = sequence.FeatureCvTermProp(
            feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id, type_id=self._date_term.cvterm_id, value=date)
        date_feature_cvtermprop_entry = self._handle_feature_cvtermprop(
            new_feature_cvtermprop_entry, existing_feature_cvtermprops, "date")

        # Insert/update entry for 'evidence'
        evidence_code = self._convert_evidence_code(gaf_record["Evidence"])
        new_feature_cvtermprop_entry = sequence.FeatureCvTermProp(
            feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id, type_id=self._evidence_term.cvterm_id,
            value=evidence_code)
        evidence_feature_cvtermprop_entry = self._handle_feature_cvtermprop(
            new_feature_cvtermprop_entry, existing_feature_cvtermprops, "evidence")

        return [date_feature_cvtermprop_entry, evidence_feature_cvtermprop_entry]

    def _handle_crossrefs(self, gaf_record: dict, feature_cvterm_entry: sequence.FeatureCvTerm
                          ) -> List[sequence.FeatureCvTermDbxRef]:
        """Inserts or updates an entry in the 'feature_cvterm_dbxref' table and returns it"""

        # Extract existing cross references for this feature_cvterm from the database
        existing_feature_cvterm_dbxrefs = self.query_all(sequence.FeatureCvTermDbxRef,
                                                         feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id)
        all_feature_cvterm_dbxrefs = []

        # Loop over all cross references of the given GAF record
        for crossref in gaf_record["With"]:

            # Split database cross reference (dbxref) into db, accession, version
            if not crossref.strip():
                continue
            (db_authority, accession, version) = ontology.split_dbxref(crossref)

            # Insert/update entry in the 'db' table
            new_db_entry = general.Db(name=db_authority)
            db_entry = self._handle_db(new_db_entry)

            # Insert/update entry in the 'dbxref' table
            new_dbxref_entry = general.DbxRef(db_id=db_entry.db_id, accession=accession, version=version)
            dbxref_entry = self._handle_dbxref(new_dbxref_entry, db_authority)

            # Insert/update entry in the 'feature_cvterm_dbxref' table
            new_feature_cvterm_dbxref_entry = sequence.FeatureCvTermDbxRef(
                feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id, dbxref_id=dbxref_entry.dbxref_id)
            feature_cvterm_dbxref_entry = self._handle_feature_cvterm_dbxref(
                new_feature_cvterm_dbxref_entry, existing_feature_cvterm_dbxrefs, crossref)
            all_feature_cvterm_dbxrefs.append(feature_cvterm_dbxref_entry)

        return all_feature_cvterm_dbxrefs

    def _handle_publications(self, gaf_record: dict, feature_cvterm_entry: sequence.FeatureCvTerm
                             ) -> List[sequence.FeatureCvTermPub]:
        """Inserts or updates entries in the 'feature_cvterm_pub' table and returns them"""

        # Extract existing publications for this feature_cvterm from the database
        existing_feature_cvterm_pubs = self.query_all(sequence.FeatureCvTermPub,
                                                      feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id)
        all_feature_cvterm_pubs = []

        # Loop over all publications of the given GAF record
        publications = gaf_record["DB:Reference"][1:]
        for publication in publications:

            # Insert/update entry in the 'pub' table
            new_pub_entry = pub.Pub(uniquename=publication, type_id=self._default_pub.type_id)
            pub_entry = self._handle_pub(new_pub_entry)

            # Insert/update entry in the 'feature_cvterm_pub' table
            new_feature_cvterm_pub_entry = sequence.FeatureCvTermPub(
                feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id, pub_id=pub_entry.pub_id)
            feature_cvterm_pub_entry = self._handle_feature_cvterm_pub(
                new_feature_cvterm_pub_entry, existing_feature_cvterm_pubs, publication)
            all_feature_cvterm_pubs.append(feature_cvterm_pub_entry)

        return all_feature_cvterm_pubs

    def _convert_evidence_code(self, abbreviation: str) -> str:
        """Converts the abbreviation for an evidence code into the spelled-out version, if applicable"""
        if abbreviation in self._evidence_codes():
            return self._evidence_codes()[abbreviation]
        return abbreviation

    @staticmethod
    def _evidence_codes() -> Dict[str, str]:
        """Lists the GO evidence codes and their respective abbreviations"""
        return {
            "EXP": "Inferred from Experiment",
            "IDA": "Inferred from Direct Assay",
            "IPI": "Inferred from Physical Interaction",
            "IMP": "Inferred from Mutant Phenotype",
            "IGI": "Inferred from Genetic Interaction",
            "IEP": "Inferred from Expression Pattern",
            "HTP": "Inferred from High Throughput Experiment",
            "HDA": "Inferred from High Throughput Direct Assay",
            "HMP": "Inferred from High Throughput Mutant Phenotype",
            "HGI": "Inferred from High Throughput Genetic Interaction",
            "HEP": "Inferred from High Throughput Expression Pattern",
            "ISS": "Inferred from Sequence or structural Similarity",
            "ISO": "Inferred from Sequence Orthology",
            "ISA": "Inferred from Sequence Alignment",
            "ISM": "Inferred from Sequence Model",
            "IGC": "Inferred from Genomic Context",
            "IBA": "Inferred from Biological aspect of Ancestor",
            "IBD": "Inferred from Biological aspect of Descendant",
            "IKR": "Inferred from Key Residues",
            "IRD": "Inferred from Rapid Divergence",
            "RCA": "Inferred from Reviewed Computational Analysis",
            "TAS": "Traceable Author Statement",
            "NAS": "Non-traceable Author Statement",
            "IC": "Inferred by Curator",
            "ND": "No biological Data available",
            "IEA": "Inferred from Electronic Annotation"
        }
