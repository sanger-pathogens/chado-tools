import unittest
from .. import dbutils, utils
from ..io import essentials
from ..orm import base, general, cv, pub


class TestEssentials(unittest.TestCase):
    """Tests various functions used to load an ontology from a file into a database"""

    connection_parameters = utils.parse_yaml(dbutils.default_configuration_file())
    connection_uri = dbutils.random_database_uri(connection_parameters)

    @classmethod
    def setUpClass(cls):
        # Creates a database, establishes a connection, and creates tables
        dbutils.create_database(cls.connection_uri)
        schema_base = base.PublicBase
        schema_metadata = schema_base.metadata
        cls.client = essentials.EssentialsClient(cls.connection_uri)
        schema_metadata.create_all(cls.client.engine, tables=schema_metadata.sorted_tables)

    @classmethod
    def tearDownClass(cls):
        # Drops the database
        dbutils.drop_database(cls.connection_uri, True)

    def tearDown(self):
        # Rolls back all changes to the database
        self.client.session.rollback()

    def test_load_generic_entries(self):
        # Tests the loading of default entries into the main tables of the Chado database
        self.client._load_generic_entries()
        null_db = self.client.query_first(general.Db)                                       # type: general.Db
        self.assertIsNotNone(null_db.db_id)
        self.assertEqual(null_db.name, "null")
        null_dbxref = self.client.query_first(general.DbxRef)                               # type: general.DbxRef
        self.assertIsNotNone(null_dbxref.dbxref_id)
        self.assertEqual(null_dbxref.accession, "null")
        null_cv = self.client.query_first(cv.Cv)                                            # type: cv.Cv
        self.assertIsNotNone(null_cv.cv_id)
        self.assertEqual(null_cv.name, "null")
        null_cvterm = self.client.query_first(cv.CvTerm)                                    # type: cv.CvTerm
        self.assertIsNotNone(null_cvterm.cvterm_id)
        self.assertEqual(null_cvterm.name, "null")
        null_pub = self.client.query_first(pub.Pub)                                         # type: pub.Pub
        self.assertIsNotNone(null_pub.pub_id)
        self.assertEqual(null_pub.uniquename, "null")

    def test_load_relationship_entries(self):
        # Tests the loading of relationship entries into the Chado 'cvterm' table
        self.client._load_relationship_entries()
        relationship_cv = self.client.query_first(cv.Cv, name="relationship")               # type: cv.Cv
        self.assertIsNotNone(relationship_cv.cv_id)
        is_a_term = self.client.query_first(cv.CvTerm, name="is_a")                         # type: cv.CvTerm
        self.assertIsNotNone(is_a_term.cvterm_id)
        self.assertEqual(is_a_term.cv_id, relationship_cv.cv_id)
        self.assertEqual(is_a_term.is_relationshiptype, 1)
        self.client._load_relationship_entries("has_part")
        has_part_term = self.client.query_first(cv.CvTerm, name="has_part")                 # type: cv.CvTerm
        self.assertIsNotNone(has_part_term.cvterm_id)

    def test_load_synonymtype_entries(self):
        # Tests the loading of synonym type entries into the Chado 'cvterm' table
        self.client._load_synonymtype_entries()
        synonym_type_cv = self.client.query_first(cv.Cv, name="synonym_type")               # type: cv.Cv
        self.assertIsNotNone(synonym_type_cv.cv_id)
        narrow_cvterm = self.client.query_first(cv.CvTerm, name="narrow")                   # type: cv.CvTerm
        self.assertIsNotNone(narrow_cvterm.cvterm_id)
        self.assertEqual(narrow_cvterm.cv_id, synonym_type_cv.cv_id)

    def test_load_cvterm_property_type_entries(self):
        # Tests the loading of cvterm property type entries into the Chado 'cvterm' table
        self.client._load_cvterm_property_type_entries()
        property_type_cv = self.client.query_first(cv.Cv, name="cvterm_property_type")      # type: cv.Cv
        self.assertIsNotNone(property_type_cv.cv_id)
        symmetric_cvterm = self.client.query_first(cv.CvTerm, name="is_symmetric")          # type: cv.CvTerm
        self.assertIsNotNone(symmetric_cvterm.cvterm_id)
        self.assertEqual(symmetric_cvterm.cv_id, property_type_cv.cv_id)
        self.assertEqual(symmetric_cvterm.is_relationshiptype, 0)
        disjoint_cvterm = self.client.query_first(cv.CvTerm, name="disjoint_from")          # type: cv.CvTerm
        self.assertIsNotNone(disjoint_cvterm.cvterm_id)
        self.assertEqual(disjoint_cvterm.cv_id, property_type_cv.cv_id)
        self.assertEqual(disjoint_cvterm.is_relationshiptype, 1)

    def test_load_feature_property_entries(self):
        # Tests the loading of feature property entries into the Chado 'cvterm' table
        self.client._load_feature_property_entries()
        feature_property_cv = self.client.query_first(cv.Cv, name="feature_property")       # type: cv.Cv
        self.assertIsNotNone(feature_property_cv.cv_id)
        comment_cvterm = self.client.query_first(cv.CvTerm, name="comment")                 # type: cv.CvTerm
        self.assertIsNotNone(comment_cvterm.cvterm_id)
        self.assertEqual(comment_cvterm.cv_id, feature_property_cv.cv_id)

    def test_load_genedb_synonymtype_entries(self):
        # Tests the loading of specific GeneDB synonym type entries into the Chado 'cvterm' table
        self.client._load_genedb_synonymtype_entries()
        synonym_type_cv = self.client.query_first(cv.Cv, name="genedb_synonym_type")        # type: cv.Cv
        self.assertIsNotNone(synonym_type_cv.cv_id)
        systematic_id_cvterm = self.client.query_first(cv.CvTerm, name="systematic_id")     # type: cv.CvTerm
        self.assertIsNotNone(systematic_id_cvterm.cvterm_id)
        self.assertEqual(systematic_id_cvterm.cv_id, synonym_type_cv.cv_id)

    def test_load_genedb_misc_entries(self):
        # Tests the loading of GeneDB-specific entries into the Chado 'cvterm' table
        self.client._load_genedb_misc_entries()
        misc_cv = self.client.query_first(cv.Cv, name="genedb_misc")                        # type: cv.Cv
        self.assertIsNotNone(misc_cv.cv_id)
        top_level_seq_cvterm = self.client.query_first(cv.CvTerm, name="top_level_seq")     # type: cv.CvTerm
        self.assertIsNotNone(top_level_seq_cvterm.cvterm_id)
        self.assertEqual(top_level_seq_cvterm.cv_id, misc_cv.cv_id)
