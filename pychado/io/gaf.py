from typing import List, Set, Dict, Union
from Bio.UniProt import GOA
from . import iobase, ontology
from .. import utils
from ..orm import general, cv, organism, pub, sequence


class GAFClient(iobase.ChadoClient):

    def __init__(self, uri: str, verbose=False, test_environment=False):
        """Constructor"""

        # Connect to database
        self.test_environment = test_environment
        if self.test_environment:
            self.printer = utils.VerbosePrinter(verbose)
        else:
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
        self._part_of_term = self._load_cvterm_from_cv("part_of", "relationship")
        self._derives_from_term = self._load_cvterm_from_cv("derives_from", "sequence")
        self._date_term = self._load_cvterm("date")
        self._evidence_term = self._load_cvterm("evidence")
        self._assigned_by_term = self._load_cvterm("assigned_by")
        self._synonym_term = self._load_cvterm("synonym")
        self._taxon_term = self._load_cvterm("taxonId")
        self._default_pub = self._load_pub("null")
        self._go_db = self._load_db("GO")
        self._product_db = self._load_db("PRODUCT")

    def _extract_feature_type(self, feature_entry: sequence.Feature) -> str:
        """Extracts the type of a feature by a database query"""
        cvterm_entry = self.query_first(cv.CvTerm, cvterm_id=feature_entry.type_id)
        return cvterm_entry.name

    def _is_featuretype_valid(self, feature_entry: sequence.Feature) -> bool:
        """Checks if a feature has a valid type"""
        featuretype = self._extract_feature_type(feature_entry)
        valid_featuretypes = self._gene_types() + self._transcript_types() + self._protein_types()
        if featuretype.lower() not in valid_featuretypes:
            return False
        return True

    def _extract_requested_feature(self, feature_entry: sequence.Feature, annotation_level: str
                                   ) -> sequence.Feature:
        """Extracts a gene, transcript or protein entry from the database, depending on the desired annotation level"""
        if annotation_level == "gene":
            requested_entry = self._extract_gene_of_feature(feature_entry)
        elif annotation_level == "transcript":
            requested_entry = self._extract_transcript_of_feature(feature_entry)
        elif annotation_level == "protein":
            requested_entry = self._extract_polypeptide_of_feature(feature_entry)
        else:
            requested_entry = feature_entry
        if not requested_entry:
            self.printer.print("WARNING: No " + annotation_level + " associated with feature '"
                               + feature_entry.uniquename + "' available in the database.")
            requested_entry = feature_entry
        return requested_entry

    def _extract_gene_of_feature(self, feature_entry: sequence.Feature) -> Union[None, sequence.Feature]:
        """Extracts the gene entry for a given feature, which can be a gene, transcript or polypeptide"""
        featuretype = self._extract_feature_type(feature_entry)
        if featuretype.lower() in self._gene_types():
            gene_entry = feature_entry
        elif featuretype.lower() in self._transcript_types():
            gene_entry = self.query_parent_features(feature_entry.feature_id, [self._part_of_term.cvterm_id]).first()
        elif featuretype.lower() in self._protein_types():
            transcript_entry = self.query_parent_features(
                feature_entry.feature_id, [self._derives_from_term.cvterm_id]).first()
            if transcript_entry:
                gene_entry = self.query_parent_features(
                    transcript_entry.feature_id, [self._part_of_term.cvterm_id]).first()
            else:
                gene_entry = None
        else:
            gene_entry = None
        return gene_entry

    def _extract_transcript_of_feature(self, feature_entry: sequence.Feature) -> Union[None, sequence.Feature]:
        """Extracts the transcript entry for a given feature, which can be a gene, transcript or polypeptide"""
        featuretype = self._extract_feature_type(feature_entry)
        if featuretype.lower() in self._gene_types():
            transcript_entry = self.query_child_features(feature_entry.feature_id, self._part_of_term.cvterm_id).first()
        elif featuretype.lower() in self._transcript_types():
            transcript_entry = feature_entry
        elif featuretype.lower() in self._protein_types():
            transcript_entry = self.query_parent_features(
                feature_entry.feature_id, [self._derives_from_term.cvterm_id]).first()
        else:
            transcript_entry = None
        return transcript_entry

    def _extract_polypeptide_of_feature(self, feature_entry: sequence.Feature) -> Union[None, sequence.Feature]:
        """Extracts the polypeptide entry for a given feature, which can be a gene, transcript or polypeptide"""
        featuretype = self._extract_feature_type(feature_entry)
        if featuretype.lower() in self._gene_types():
            transcript_entry = self.query_child_features(feature_entry.feature_id, self._part_of_term.cvterm_id).first()
            if transcript_entry:
                polypeptide_entry = self.query_child_features(
                    transcript_entry.feature_id, self._derives_from_term.cvterm_id).first()
            else:
                polypeptide_entry = None
        elif featuretype.lower() in self._transcript_types():
            polypeptide_entry = self.query_child_features(
                feature_entry.feature_id, self._derives_from_term.cvterm_id).first()
        elif featuretype.lower() in self._protein_types():
            polypeptide_entry = feature_entry
        else:
            polypeptide_entry = None
        return polypeptide_entry

    def _convert_evidence_code(self, abbreviation: str) -> str:
        """Converts the abbreviation for an evidence code into the spelled-out version, if applicable"""
        if abbreviation in self._abbreviations_to_evidence_codes():
            return self._abbreviations_to_evidence_codes()[abbreviation]
        return ""

    def _back_convert_evidence_code(self, evidence_code: str) -> str:
        """Converts a spelled-out evidence code into its abbreviation, if applicable"""
        if evidence_code.lower() in self._evidence_codes_to_abbreviations():
            return self._evidence_codes_to_abbreviations()[evidence_code.lower()]
        if evidence_code.upper() in self._abbreviations_to_evidence_codes():
            return evidence_code.upper()
        return ""

    def _convert_namespace(self, namespace: str) -> str:
        """Converts a GO namespace into its abbreviation, if applicable"""
        if namespace in self._namespace_to_abbreviation():
            return self._namespace_to_abbreviation()[namespace]
        return ""

    @staticmethod
    def _abbreviations_to_evidence_codes() -> Dict[str, str]:
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
            "IEA": "Inferred from Electronic Annotation",
            "NR": "Not recorded"
        }

    @staticmethod
    def _default_evidence_code() -> str:
        """Yields the default GO evidence code"""
        return "NR"

    def _evidence_codes_to_abbreviations(self) -> Dict[str, str]:
        """Lists the GO evidence codes and their respective abbreviations"""
        return {
            evidence_code.lower(): abbreviation
            for abbreviation, evidence_code
            in self._abbreviations_to_evidence_codes().items()
        }

    @staticmethod
    def _namespace_to_abbreviation() -> Dict[str, str]:
        """Lists the GO namespaces and their respective abbreviations"""
        return {
            "cellular_component": "C",
            "molecular_function": "F",
            "biological_process": "P"
        }

    @staticmethod
    def _db_reference_identifiers() -> List[str]:
        """Lists the permitted database authorities for the GAF DB:Reference column"""
        return ["PMID", "GO_REF", "SGD_REF"]

    @staticmethod
    def _default_db_reference() -> str:
        """Yields the default value for the GAF DB:Reference column"""
        return "GO_REF:0000002"

    @staticmethod
    def _gene_types() -> List[str]:
        """Lists considered gene types"""
        return ["gene", "pseudogene"]

    @staticmethod
    def _transcript_types() -> List[str]:
        """Lists considered transcript types"""
        return ["mrna", "rrna", "trna", "snrna", "ncrna", "scrna", "snorna", "pseudogenic_transcript"]

    @staticmethod
    def _protein_types() -> List[str]:
        """Lists considered protein types"""
        return ["polypeptide"]


class GAFImportClient(GAFClient):
    """Class for importing genomic data from GAF files into Chado"""

    def load(self, filename: str, organism_name: str, annotation_level: str):
        """Import data from a GAF file into a Chado database"""

        # Load dependencies
        default_organism = self._load_organism(organism_name)
        features_with_product = set()

        # Loop over all records in the GAF file
        with open(filename) as f:
            for gaf_record in GOA.gafiterator(f):

                # Import this record into the database
                self._load_gaf_record(gaf_record, default_organism, annotation_level, features_with_product)

        # Commit changes
        self.session.commit()

    def _load_gaf_record(self, gaf_record: dict, organism_entry: organism.Organism, annotation_level: str,
                         features_with_product: Set[str]) -> None:
        """Imports data from a GAF record into a Chado database"""

        # Get the feature entries
        gaf_feature_entry = self._load_feature(gaf_record, organism_entry)
        if not gaf_feature_entry:
            return
        requested_feature_entry = self._extract_requested_feature(gaf_feature_entry, annotation_level)
        gene_feature_entry = self._extract_gene_of_feature(requested_feature_entry)

        # Update/insert gene name and synonym(s)
        self._handle_name(gaf_record, gene_feature_entry)
        self._handle_synonyms(gaf_record, gene_feature_entry)

        # Update/insert a feature_cvterm entry for the gene product
        if requested_feature_entry.uniquename not in features_with_product:
            self._handle_product_term(gaf_record, requested_feature_entry)
            features_with_product.add(requested_feature_entry.uniquename)

        # Update/insert a feature_cvterm entry for the ontology term
        feature_cvterm_entry = self._handle_ontology_term(gaf_record, requested_feature_entry)
        if not feature_cvterm_entry:
            return

        # Update/insert feature_cvtermprop entries for date, evidence code and assigning database
        self._handle_properties(gaf_record, feature_cvterm_entry, requested_feature_entry)

        # Update/insert feature_cvterm_dbxref entries
        self._handle_crossrefs(gaf_record, feature_cvterm_entry, requested_feature_entry)

        # Update/insert feature_cvterm_pub entries
        self._handle_publications(gaf_record, feature_cvterm_entry, requested_feature_entry)

    def _load_feature(self, gaf_record: dict, organism_entry: organism.Organism) -> Union[None, sequence.Feature]:
        """Loads a feature entry from the database"""
        feature_name = gaf_record["DB_Object_ID"].strip()
        if not feature_name:
            return None
        feature_entry = self.query_first(sequence.Feature, organism_id=organism_entry.organism_id,
                                         uniquename=feature_name)
        return feature_entry

    def _handle_name(self, gaf_record: dict, feature_entry: sequence.Feature) -> None:
        """Inserts or updates the name of a feature"""
        name = gaf_record["DB_Object_Symbol"].strip()
        if name and name != feature_entry.uniquename and name != feature_entry.name:
            feature_entry.name = name
            self.printer.print("Updated name '" + feature_entry.name + "' for feature '"
                               + feature_entry.uniquename + "'")

    def _handle_synonyms(self, gaf_record: dict, feature_entry: sequence.Feature) -> List[sequence.FeatureSynonym]:
        """Inserts or updates entries in the 'synonym' and 'feature_synonym' tables and returns the latter"""

        # Extract existing synonyms for this feature from the database
        existing_feature_synonyms = self.query_feature_synonym_by_type(
            feature_entry.feature_id, [self._synonym_term.cvterm_id]).all()
        all_feature_synonyms = []

        # Loop over all synonyms for this feature in the GFF record
        synonyms = gaf_record["Synonym"]
        for synonym in synonyms:

            # Insert/update entry in the 'synonym' table
            if not synonym.strip():
                continue
            new_synonym_entry = sequence.Synonym(name=synonym, type_id=self._synonym_term.cvterm_id,
                                                 synonym_sgml=synonym)
            synonym_entry = self._handle_synonym(new_synonym_entry)

            # Insert/update entry in the 'feature_synonym' table
            new_feature_synonym_entry = sequence.FeatureSynonym(
                synonym_id=synonym_entry.synonym_id, feature_id=feature_entry.feature_id,
                pub_id=self._default_pub.pub_id)
            feature_synonym_entry = self._handle_feature_synonym(new_feature_synonym_entry, existing_feature_synonyms,
                                                                 synonym, feature_entry.uniquename)
            all_feature_synonyms.append(feature_synonym_entry)

        return all_feature_synonyms

    def _handle_ontology_term(self, gaf_record: dict, feature_entry: sequence.Feature
                              ) -> Union[None, sequence.FeatureCvTerm]:
        """Inserts or updates an entry in the 'feature_cvterm' table and returns it"""

        # Extract ontology identifier from the GAF record and split it into db, accession, version
        ontology_term = gaf_record["GO_ID"].strip()
        (db_authority, accession, version) = ontology.split_dbxref(ontology_term)
        publication = self._extract_primary_publication(gaf_record)

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
            feature_entry.feature_id, db_entry.db_id).all()

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
        publication = self._extract_primary_publication(gaf_record)

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
            feature_entry.feature_id, db_entry.db_id).all()

        # Insert/update entry in the 'feature_cvterm' table
        new_feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=feature_entry.feature_id,
                                                          cvterm_id=cvterm_entry.cvterm_id,
                                                          pub_id=pub_entry.pub_id)
        feature_cvterm_entry = self._handle_feature_cvterm(new_feature_cvterm_entry, existing_feature_cvterms,
                                                           cvterm_entry.name, feature_entry.uniquename)
        return feature_cvterm_entry

    def _handle_properties(self, gaf_record: dict, feature_cvterm_entry: sequence.FeatureCvTerm,
                           feature_entry: sequence.Feature) -> List[sequence.FeatureCvTermProp]:
        """Inserts or updates entries in the 'feature_cvtermprop' table and returns them"""

        # Extract existing properties for this feature_cvterm from the database
        existing_feature_cvtermprops = self.query_all(sequence.FeatureCvTermProp,
                                                      feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id)

        # Insert/update entry for 'date'
        date = gaf_record["Date"].strip()
        new_feature_cvtermprop_entry = sequence.FeatureCvTermProp(
            feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id, type_id=self._date_term.cvterm_id, value=date)
        date_feature_cvtermprop_entry = self._handle_feature_cvtermprop(
            new_feature_cvtermprop_entry, existing_feature_cvtermprops, "date", feature_entry.uniquename)

        # Insert/update entry for 'evidence'
        evidence_code = self._convert_evidence_code(gaf_record["Evidence"])
        new_feature_cvtermprop_entry = sequence.FeatureCvTermProp(
            feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id, type_id=self._evidence_term.cvterm_id,
            value=evidence_code)
        evidence_feature_cvtermprop_entry = self._handle_feature_cvtermprop(
            new_feature_cvtermprop_entry, existing_feature_cvtermprops, "evidence", feature_entry.uniquename)

        # Insert/update entry for 'assigned_by'
        assigning_db = gaf_record["Assigned_By"].strip()
        new_feature_cvtermprop_entry = sequence.FeatureCvTermProp(
            feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id, type_id=self._assigned_by_term.cvterm_id,
            value=assigning_db)
        assigned_by_feature_cvtermprop_entry = self._handle_feature_cvtermprop(
            new_feature_cvtermprop_entry, existing_feature_cvtermprops, "assigned_by", feature_entry.uniquename)

        return [date_feature_cvtermprop_entry, evidence_feature_cvtermprop_entry, assigned_by_feature_cvtermprop_entry]

    def _handle_crossrefs(self, gaf_record: dict, feature_cvterm_entry: sequence.FeatureCvTerm,
                          feature_entry: sequence.Feature) -> List[sequence.FeatureCvTermDbxRef]:
        """Inserts or updates an entry in the 'feature_cvterm_dbxref' table and returns it"""

        # Extract existing cross references for this feature_cvterm from the database
        existing_feature_cvterm_dbxrefs = self.query_all(sequence.FeatureCvTermDbxRef,
                                                         feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id)
        all_feature_cvterm_dbxrefs = []

        # Loop over all cross references of the given GAF record
        crossrefs = self._extract_cross_references(gaf_record)
        for crossref in crossrefs:

            # Split database cross reference (dbxref) into db, accession, version
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
                new_feature_cvterm_dbxref_entry, existing_feature_cvterm_dbxrefs, crossref, feature_entry.uniquename)
            all_feature_cvterm_dbxrefs.append(feature_cvterm_dbxref_entry)

        return all_feature_cvterm_dbxrefs

    def _handle_publications(self, gaf_record: dict, feature_cvterm_entry: sequence.FeatureCvTerm,
                             feature_entry: sequence.Feature) -> List[sequence.FeatureCvTermPub]:
        """Inserts or updates entries in the 'feature_cvterm_pub' table and returns them"""

        # Extract existing publications for this feature_cvterm from the database
        existing_feature_cvterm_pubs = self.query_all(sequence.FeatureCvTermPub,
                                                      feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id)
        all_feature_cvterm_pubs = []

        # Loop over all publications of the given GAF record
        publications = self._extract_secondary_publications(gaf_record)
        for publication in publications:

            # Insert/update entry in the 'pub' table
            new_pub_entry = pub.Pub(uniquename=publication, type_id=self._default_pub.type_id)
            pub_entry = self._handle_pub(new_pub_entry)

            # Insert/update entry in the 'feature_cvterm_pub' table
            new_feature_cvterm_pub_entry = sequence.FeatureCvTermPub(
                feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id, pub_id=pub_entry.pub_id)
            feature_cvterm_pub_entry = self._handle_feature_cvterm_pub(
                new_feature_cvterm_pub_entry, existing_feature_cvterm_pubs, publication, feature_entry.uniquename)
            all_feature_cvterm_pubs.append(feature_cvterm_pub_entry)

        return all_feature_cvterm_pubs

    def _extract_cross_references(self, gaf_record: dict) -> List[str]:
        """Extracts the database cross references of a GAF record"""
        potential_crossrefs = gaf_record["With"] + gaf_record["DB:Reference"]
        crossrefs = []
        pubs = [self._extract_primary_publication(gaf_record)] + self._extract_secondary_publications(gaf_record)
        for crossref in potential_crossrefs:
            if crossref.strip() and crossref not in pubs:
                crossrefs.append(crossref)
        return crossrefs

    @staticmethod
    def _extract_primary_publication(gaf_record: dict) -> Union[None, str]:
        """Extracts the primary publication of a GAF record"""
        potential_publications = gaf_record["DB:Reference"]
        for publication in potential_publications:
            if ":" not in publication:
                return publication.strip()
            (db_authority, accession, version) = ontology.split_dbxref(publication)
            if db_authority == "PMID":
                return publication.strip()
        return None

    @staticmethod
    def _extract_secondary_publications(gaf_record: dict) -> List[str]:
        """Extracts the secondary publications of a GAF record"""
        potential_publications = gaf_record["DB:Reference"]
        secondary_publications = []
        for publication in potential_publications:
            if ":" not in publication:
                secondary_publications.append(publication.strip())
                continue
            (db_authority, accession, version) = ontology.split_dbxref(publication)
            if db_authority == "PMID":
                secondary_publications.append(publication.strip())
        if secondary_publications:
            return secondary_publications[1:]
        else:
            return secondary_publications


class GAFExportClient(GAFClient):
    """Class for exporting gene annotation data from Chado to GAF files"""

    def export(self, gaf_filename: str, organism_name: str, database_authority: str, annotation_level: str,
               include_obsolete_features=False) -> None:

        # Load dependencies
        organism_entry = self._load_organism(organism_name)
        taxon_id = self._extract_taxon_id(organism_entry)

        # Open GAF file and write header
        with utils.open_file_write(gaf_filename) as gaf_handle:
            self._write_gaf_header(gaf_handle)

            # Get all feature_cvterms associated with GO terms
            go_feature_cvterm_entries = self.query_feature_cvterm_by_ontology_and_organism(
                organism_entry.organism_id, self._go_db.db_id).order_by(
                sequence.Feature.uniquename, general.DbxRef.accession).all()

            # Loop over all feature_cvterms
            for go_feature_cvterm_entry in go_feature_cvterm_entries:

                # Create a GFF record for this feature_cvterm
                go_feature_entry = self.query_first(sequence.Feature, feature_id=go_feature_cvterm_entry.feature_id)
                if self._is_featuretype_valid(go_feature_entry) \
                        and (include_obsolete_features or not go_feature_entry.is_obsolete):
                    self._export_gaf_record(go_feature_entry, go_feature_cvterm_entry, database_authority, taxon_id,
                                            annotation_level, gaf_handle)

        # Information
        self.printer.print("Exported GAF data for organism " + organism_name + " to " + gaf_filename + ".")

    @staticmethod
    def _write_gaf_header(file_handle):
        """Prints the header of a GAF file"""
        file_handle.write("!gaf-version: 1.0\n")

    def _export_gaf_record(self, feature_entry: sequence.Feature, feature_cvterm_entry: sequence.FeatureCvTerm,
                           database_authority: str, taxon_id: str, annotation_level: str, file_handle):
        """Exports a GAF record for a given feature and GO term"""

        try:
            # Create GAF record
            requested_feature = self._extract_requested_feature(feature_entry, annotation_level)
            gene_feature = self._extract_gene_of_feature(requested_feature)
            gaf_record = self._create_gaf_record(feature_cvterm_entry, requested_feature, database_authority, taxon_id)

            # Query various tables to gather information related to the feature_cvterm
            go_id = self._extract_feature_cvterm_ontology_term(feature_cvterm_entry)
            go_namespace = self._extract_go_namespace(feature_cvterm_entry)
            feature_cvterm_properties = self._extract_feature_cvterm_properties(feature_cvterm_entry)
            feature_cvterm_dbxrefs = self._extract_feature_cvterm_dbxrefs(feature_cvterm_entry)
            feature_cvterm_publications = self._extract_feature_cvterm_publications(feature_cvterm_entry)
            featuretype = self._extract_feature_type(requested_feature)
            gene_name = self._extract_feature_name(gene_feature)
            gene_synonyms = self._extract_feature_synonyms(gene_feature)
            product_name = self._extract_product_name(feature_entry)

            # Add attributes to the GAF record
            self._add_gaf_go_id(gaf_record, go_id)
            self._add_gaf_aspect(gaf_record, go_namespace)
            self._add_gaf_annotation_date(gaf_record, feature_cvterm_properties)
            self._add_gaf_evidence_code(gaf_record, feature_cvterm_properties)
            self._add_gaf_assigning_db(gaf_record, feature_cvterm_properties)
            self._add_gaf_withfrom_info(gaf_record, feature_cvterm_dbxrefs)
            self._add_gaf_db_references(gaf_record, feature_cvterm_publications, feature_cvterm_dbxrefs)
            self._add_gaf_object_type(gaf_record, featuretype)
            self._add_gaf_object_symbol(gaf_record, gene_name)
            self._add_gaf_synonyms(gaf_record, gene_synonyms)
            self._add_gaf_object_name(gaf_record, product_name)

            # Write the generated GAF record to file
            self._print_gaf_record(file_handle, gaf_record)

        except iobase.DatabaseError as err:
            self.printer.print(err.args)

    def _print_gaf_record(self, file_handle, gaf_record: dict):
        """Prints a GAF record to file"""
        line = "\t".join([self._stringify_gaf_attribute(value) for value in gaf_record.values()])
        file_handle.write(line + "\n")

    @staticmethod
    def _stringify_gaf_attribute(attribute: Union[str, List[str]]) -> str:
        """Converts a GAF attribute from a list to a string, separated by pipes"""
        if isinstance(attribute, str):
            return attribute
        elif isinstance(attribute, list):
            return utils.list_to_string(attribute, "|")
        else:
            return ""

    @staticmethod
    def _create_gaf_record(feature_cvterm_entry: sequence.FeatureCvTerm, feature_entry: sequence.Feature,
                           database_authority: str, taxon_id: str) -> dict:
        """Creates a GAF record"""
        gaf_record = {key: None for key in GOA.GAF10FIELDS}
        gaf_record["DB"] = database_authority
        gaf_record["DB_Object_ID"] = feature_entry.uniquename
        gaf_record["Taxon_ID"] = taxon_id
        if feature_cvterm_entry.is_not:
            gaf_record["Qualifier"] = "NOT"
        return gaf_record

    def _extract_taxon_id(self, organism_entry: organism.Organism) -> str:
        """Extracts the NCBI taxon ID associated with an organism"""
        taxon_id = "taxon:" + organism_entry.abbreviation
        organismprop_entry = self.query_first(organism.OrganismProp, organism_id=organism_entry.organism_id,
                                              type_id=self._taxon_term.cvterm_id)
        if organismprop_entry:
            taxon_id = "taxon:" + organismprop_entry.value
        return taxon_id

    def _extract_feature_cvterm_ontology_term(self, feature_cvterm_entry: sequence.FeatureCvTerm) -> str:
        """Extracts the ontology term associated with a feature_cvterm by a database query"""
        db_and_accession = self.query_feature_cvterm_ontology_terms(
            feature_cvterm_entry.feature_cvterm_id, self._go_db.db_id).first()
        ontology_term = ""
        if db_and_accession:
            ontology_term = ontology.create_dbxref(db_and_accession[0], db_and_accession[1])
        return ontology_term

    def _extract_feature_cvterm_properties(self, feature_cvterm_entry: sequence.FeatureCvTerm) -> Dict[str, str]:
        """Extracts properties associated with a feature_cvterm by a database query"""
        properties = {}
        for property_type, property_value in self.query_feature_cvterm_properties(
                feature_cvterm_entry.feature_cvterm_id).all():
            properties[property_type] = property_value
        return properties

    def _extract_feature_cvterm_dbxrefs(self, feature_cvterm_entry: sequence.FeatureCvTerm) -> List[str]:
        """Extracts database cross references associated with a feature_cvterm by a database query"""
        cross_references = []
        for db_authority, accession in self.query_feature_cvterm_dbxrefs(feature_cvterm_entry.feature_cvterm_id).all():
            crossref = ontology.create_dbxref(db_authority, accession)
            cross_references.append(crossref)
        return cross_references

    def _extract_feature_cvterm_publications(self, feature_cvterm_entry: sequence.FeatureCvTerm) -> List[str]:
        """Extracts publications associated with a feature_cvterm by a database query"""
        publications = []
        for publication, in self.query_feature_cvterm_pubs(feature_cvterm_entry.feature_cvterm_id).all():
            publications.append(publication)
        for publication, in self.query_feature_cvterm_secondary_pubs(feature_cvterm_entry.feature_cvterm_id).all():
            publications.append(publication)
        return publications

    def _extract_go_namespace(self, feature_cvterm_entry: sequence.FeatureCvTerm) -> str:
        """Extracts the namespace of a feature_cvterm by a database query"""
        return self.query_cvterm_namespace(feature_cvterm_entry.cvterm_id).scalar()

    @staticmethod
    def _extract_feature_name(feature_entry: sequence.Feature) -> str:
        """Extracts the name of a given feature"""
        name = ""
        if feature_entry:
            name = feature_entry.name or feature_entry.uniquename
        return name

    def _extract_feature_synonyms(self, feature_entry: sequence.Feature) -> List[str]:
        """Extracts synonyms of a feature by a database query"""
        synonyms = []
        if feature_entry:
            for synonym_type, synonym_name in self.query_feature_synonyms(feature_entry.feature_id).all():
                synonyms.append(synonym_name)
        return synonyms

    def _extract_product_name(self, feature_entry: sequence.Feature) -> str:
        """Extracts the gene product of a feature by a database query"""
        name = ""
        product_feature_cvterm = self.query_feature_cvterm_by_ontology(
            feature_entry.feature_id, self._product_db.db_id).first()
        if product_feature_cvterm:
            name = self.query_first(cv.CvTerm, cvterm_id=product_feature_cvterm.cvterm_id).name
        return name

    @staticmethod
    def _add_gaf_go_id(gaf_record: dict, go_id: str) -> None:
        """Adds the GO term to a GAF record"""
        if not go_id:
            raise iobase.DatabaseError("Missing ontology term for feature '" + gaf_record["DB_Object_ID"] + "'")
        gaf_record["GO_ID"] = go_id

    def _add_gaf_aspect(self, gaf_record: dict, namespace: str) -> None:
        """Adds the 'aspect' (GO namespace) to a GAF record"""
        aspect = self._convert_namespace(namespace)
        if not aspect:
            raise iobase.DatabaseError("Unrecognized GO namespace: '" + namespace + "' for GO term '"
                                       + gaf_record["GO_ID"] + "'")
        gaf_record["Aspect"] = aspect

    def _add_gaf_annotation_date(self, gaf_record: dict, properties: Dict[str, str]) -> None:
        """Adds the annotation date to a GAF record"""
        if "date" not in properties:
            self.printer.print("Missing annotation date for feature '" + gaf_record["DB_Object_ID"]
                               + "' and GO term '" + gaf_record["GO_ID"] + "'")
            gaf_record["Date"] = utils.current_date()
        else:
            gaf_record["Date"] = properties["date"]

    def _add_gaf_evidence_code(self, gaf_record: dict, properties: Dict[str, str]) -> None:
        """Adds the GO evidence code to a GAF record"""
        if "evidence" not in properties:
            self.printer.print("Missing evidence code for feature '" + gaf_record["DB_Object_ID"] + "' and GO term '"
                               + gaf_record["GO_ID"] + "'")
            gaf_record["Evidence"] = self._default_evidence_code()
        else:
            evidence_code = self._back_convert_evidence_code(properties["evidence"])
            if not evidence_code:
                self.printer.print("Unrecognized evidence code: '" + properties["evidence"] + "' for feature '"
                                   + gaf_record["DB_Object_ID"] + "' and GO term '" + gaf_record["GO_ID"] + "'")
                gaf_record["Evidence"] = self._default_evidence_code()
            else:
                gaf_record["Evidence"] = evidence_code

    @staticmethod
    def _add_gaf_assigning_db(gaf_record: dict, properties: Dict[str, str]) -> None:
        """Adds the assigning database to a GAF record"""
        if "assigned_by" not in properties:
            gaf_record["Assigned_By"] = gaf_record["DB"]
        else:
            gaf_record["Assigned_By"] = properties["assigned_by"]

    def _add_gaf_db_references(self, gaf_record: dict, publications: List[str], dbxrefs: List[str]) -> None:
        """Adds reference IDs to a GAF record"""
        gaf_record["DB:Reference"] = []
        for publication in publications:
            if publication != "null":
                gaf_record["DB:Reference"].append(publication)
        for dbxref in dbxrefs:
            db_authority = ontology.split_dbxref(dbxref)[0]
            if db_authority in self._db_reference_identifiers():
                gaf_record["DB:Reference"].append(dbxref)
        if not gaf_record["DB:Reference"]:
            gaf_record["DB:Reference"].append(self._default_db_reference())

    def _add_gaf_withfrom_info(self, gaf_record: dict, dbxrefs: List[str]) -> None:
        """Adds references for a GO evidence code to a GAF record"""
        gaf_record["With"] = []
        for dbxref in dbxrefs:
            db_authority = ontology.split_dbxref(dbxref)[0]
            if db_authority not in self._db_reference_identifiers():
                gaf_record["With"].append(dbxref)

    @staticmethod
    def _add_gaf_object_type(gaf_record: dict, featuretype: str) -> None:
        """Adds the feature type to a GAF record"""
        gaf_record["DB_Object_Type"] = featuretype

    @staticmethod
    def _add_gaf_object_name(gaf_record: dict, product_name: str) -> None:
        """Adds the name of a gene product to a GAF record"""
        gaf_record["DB_Object_Name"] = product_name

    @staticmethod
    def _add_gaf_object_symbol(gaf_record: dict, gene_name: str) -> None:
        """Adds the gene name to a GAF record"""
        if not gene_name:
            raise iobase.DatabaseError("Missing gene name for feature '" + gaf_record["DB_Object_ID"] + "'")
        gaf_record["DB_Object_Symbol"] = gene_name

    @staticmethod
    def _add_gaf_synonyms(gaf_record: dict, synonyms: List[str]) -> None:
        """Adds gene synonyms to a GAF record"""
        gaf_record["Synonym"] = synonyms
