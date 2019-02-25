from ..io import iobase
from ..orm import general, cv, pub


class EssentialsClient(iobase.ChadoClient):
    """Class for importing essential basic entries into the Chado tables"""
    
    def load(self):
        """Import essential basic entries into various database tables"""
        self._load_generic_entries()
        self._load_relationship_entries()
        self._load_synonymtype_entries()
        self._load_cvterm_property_type_entries()
        self._load_feature_property_entries()
        self._load_genedb_synonymtype_entries()
        self._load_genedb_misc_entries()
        self._load_genedb_products_vocabulary()
        self.session.commit()

    def _load_generic_entries(self):
        """Import generic entries in the db, dbxref, cv, cvterm, and pub tables"""
        new_generic_db = general.Db(name="null", description="a fake database for locally created essentials")
        generic_db = self._handle_db(new_generic_db)
        new_generic_dbxref = general.DbxRef(db_id=generic_db.db_id, accession="null")
        generic_dbxref = self._handle_dbxref(new_generic_dbxref, generic_db.name)
        new_generic_cv = cv.Cv(name="null", definition="a fake vocabulary for locally created essentials")
        generic_cv = self._handle_cv(new_generic_cv)
        new_generic_cvterm = cv.CvTerm(cv_id=generic_cv.cv_id, dbxref_id=generic_dbxref.dbxref_id, name="null")
        generic_cvterm = self._handle_cvterm(new_generic_cvterm, generic_cv.name)
        new_generic_pub = pub.Pub(uniquename="null", type_id=generic_cvterm.cvterm_id)
        self._handle_pub(new_generic_pub)

    def _load_relationship_entries(self, *further_terms):
        """Import CV terms for relationships
        (note: all other basic relationship terms are part of the RO relationship ontology)"""
        new_relationship_db = general.Db(name="RO")
        relationship_db = self._handle_db(new_relationship_db)
        new_relationship_cv = cv.Cv(name="relationship")
        relationship_cv = self._handle_cv(new_relationship_cv)

        terms = ["is_a"] + [term for term in further_terms]
        for term in terms:

            new_dbxref = general.DbxRef(db_id=relationship_db.db_id, accession=term)
            dbxref = self._handle_dbxref(new_dbxref, relationship_db.name)
            new_cvterm = cv.CvTerm(cv_id=relationship_cv.cv_id, dbxref_id=dbxref.dbxref_id, name=term,
                                   is_relationshiptype=1)
            self._handle_cvterm(new_cvterm, relationship_cv.name)

    def _load_synonymtype_entries(self):
        """Import CV terms for synonym types"""
        new_synonymtype_db = general.Db(name="internal")
        synonymtype_db = self._handle_db(new_synonymtype_db)
        new_synonymtype_cv = cv.Cv(name="synonym_type")
        synonymtype_cv = self._handle_cv(new_synonymtype_cv)

        for term in ["exact", "narrow", "broad", "related"]:

            new_dbxref = general.DbxRef(db_id=synonymtype_db.db_id, accession=term)
            dbxref = self._handle_dbxref(new_dbxref, synonymtype_db.name)
            new_cvterm = cv.CvTerm(cv_id=synonymtype_cv.cv_id, dbxref_id=dbxref.dbxref_id, name=term)
            self._handle_cvterm(new_cvterm, synonymtype_cv.name)

    def _load_cvterm_property_type_entries(self):
        """Import CV terms for property types"""
        new_propertytype_db = general.Db(name="internal")
        propertytype_db = self._handle_db(new_propertytype_db)
        new_propertytype_cv = cv.Cv(name="cvterm_property_type")
        propertytype_cv = self._handle_cv(new_propertytype_cv)

        # non-relationship types
        for term in ["comment", "is_anonymous", "is_transitive", "is_anti_symmetric", "is_reflexive", "is_symmetric",
                     "is_cyclic"]:

            new_dbxref = general.DbxRef(db_id=propertytype_db.db_id, accession=term)
            dbxref = self._handle_dbxref(new_dbxref, propertytype_db.name)
            new_cvterm = cv.CvTerm(cv_id=propertytype_cv.cv_id, dbxref_id=dbxref.dbxref_id, name=term)
            self._handle_cvterm(new_cvterm, propertytype_cv.name)

        # relationship types
        for term in ["intersection_of", "disjoint_from"]:

            new_dbxref = general.DbxRef(db_id=propertytype_db.db_id, accession=term)
            dbxref = self._handle_dbxref(new_dbxref, propertytype_db.name)
            new_cvterm = cv.CvTerm(cv_id=propertytype_cv.cv_id, dbxref_id=dbxref.dbxref_id, name=term,
                                   is_relationshiptype=1)
            self._handle_cvterm(new_cvterm, propertytype_cv.name)

    def _load_feature_property_entries(self):
        """Import CV terms for feature properties (note: these terms are also part of the SOFP ontology)"""
        new_feature_property_db = general.Db(name="SOFP")
        feature_property_db = self._handle_db(new_feature_property_db)
        new_feature_property_cv = cv.Cv(name="feature_property")
        feature_property_cv = self._handle_cv(new_feature_property_cv)

        for term in ["comment", "score", "source", "description", "date"]:

            new_dbxref = general.DbxRef(db_id=feature_property_db.db_id, accession=term)
            dbxref = self._handle_dbxref(new_dbxref, feature_property_db.name)
            new_cvterm = cv.CvTerm(cv_id=feature_property_cv.cv_id, dbxref_id=dbxref.dbxref_id, name=term)
            self._handle_cvterm(new_cvterm, feature_property_cv.name)

    def _load_genedb_synonymtype_entries(self):
        """Import CV terms for specific GeneDB synonym types"""
        new_synonymtype_db = general.Db(name="genedb_misc")
        synonymtype_db = self._handle_db(new_synonymtype_db)
        new_synonymtype_cv = cv.Cv(name="genedb_synonym_type")
        synonymtype_cv = self._handle_cv(new_synonymtype_cv)

        for term in ["synonym", "alias", "systematic_id", "previous_systematic_id", "temporary_systematic_id"]:

            new_dbxref = general.DbxRef(db_id=synonymtype_db.db_id, accession=term)
            dbxref = self._handle_dbxref(new_dbxref, synonymtype_db.name)
            new_cvterm = cv.CvTerm(cv_id=synonymtype_cv.cv_id, dbxref_id=dbxref.dbxref_id, name=term)
            self._handle_cvterm(new_cvterm, synonymtype_cv.name)

    def _load_genedb_misc_entries(self):
        """Import specific CV terms for GeneDB"""
        new_misc_db = general.Db(name="genedb_misc")
        misc_db = self._handle_db(new_misc_db)
        new_misc_cv = cv.Cv(name="genedb_misc")
        misc_cv = self._handle_cv(new_misc_cv)

        for term in ["top_level_seq", "evidence", "genedb_public", "assigned_by", "colour", "version"]:

            new_dbxref = general.DbxRef(db_id=misc_db.db_id, accession=term)
            dbxref = self._handle_dbxref(new_dbxref, misc_db.name)
            new_cvterm = cv.CvTerm(cv_id=misc_cv.cv_id, dbxref_id=dbxref.dbxref_id, name=term)
            self._handle_cvterm(new_cvterm, misc_cv.name)

    def _load_genedb_products_vocabulary(self):
        """Import CV for GeneDB products"""
        new_product_db = general.Db(name="PRODUCT")
        self._handle_db(new_product_db)
        new_product_cv = cv.Cv(name="genedb_products")
        self._handle_cv(new_product_cv)

    def _load_sequence_type_entries(self):
        """Import CV terms for sequence types; for testing only (all terms are part of the SO sequence ontology)"""
        new_sequence_db = general.Db(name="SO")
        sequence_db = self._handle_db(new_sequence_db)
        new_sequence_cv = cv.Cv(name="sequence")
        sequence_cv = self._handle_cv(new_sequence_cv)

        for term in ["gene", "intron", "exon", "CDS", "mRNA", "chromosome", "contig", "supercontig", "region"]:

            new_dbxref = general.DbxRef(db_id=sequence_db.db_id, accession=term)
            dbxref = self._handle_dbxref(new_dbxref, sequence_db.name)
            new_cvterm = cv.CvTerm(cv_id=sequence_cv.cv_id, dbxref_id=dbxref.dbxref_id, name=term)
            self._handle_cvterm(new_cvterm, sequence_cv.name)

        self.session.commit()

    def _load_further_relationship_entries(self):
        """Import further CV terms for relationships; for testing only"""
        self._load_relationship_entries("part_of", "derives_from")
        self.session.commit()
