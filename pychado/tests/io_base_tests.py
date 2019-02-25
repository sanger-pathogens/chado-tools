import unittest
import sqlalchemy.ext.declarative
from .. import dbutils, utils
from ..orm import base, general, cv, organism, pub, sequence
from ..io import iobase, essentials, direct

test_base = sqlalchemy.ext.declarative.declarative_base()


class Species(test_base):
    """ORM of a test table"""
    __tablename__ = "species"
    id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.VARCHAR(20), nullable=False)
    clade = sqlalchemy.Column(sqlalchemy.VARCHAR(20), nullable=True)
    legs = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")
    extinct = sqlalchemy.Column(sqlalchemy.BOOLEAN, nullable=False, server_default="False")

    def __init__(self, name, clade=None, legs=0, extinct=False):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)


class TestIOClient(unittest.TestCase):
    """Tests basic functions for accessing databases via SQL"""

    connection_parameters = utils.parse_yaml(dbutils.default_configuration_file())
    connection_uri = dbutils.random_database_uri(connection_parameters)

    @classmethod
    def setUpClass(cls):
        # Creates a database, establishes a connection and creates tables
        dbutils.create_database(cls.connection_uri)
        cls.client = iobase.IOClient(cls.connection_uri)
        schema_base = test_base
        schema_base.metadata.create_all(cls.client.engine)
        # self.client = io.IOClient("sqlite:///:memory:")
        # self.client.engine.execute("ATTACH DATABASE ':memory:' AS " + self.client.schema)
        # self.client.session.execute("PRAGMA foreign_keys=ON")

    @classmethod
    def tearDownClass(cls):
        # Drops the database
        dbutils.drop_database(cls.connection_uri, True)

    def tearDown(self):
        # Rolls back all changes to the database
        self.client.session.rollback()

    def test_io(self):
        # Test the basic functionality for inserting data into database tables and retrieving data from them

        # Check the table is initially empty
        empty_table = self.client.query_first(Species)
        self.assertIsNone(empty_table)

        # Add an entry using 'add_and_flush', and assert that it automatically obtains an ID
        human = Species(name="human", clade="mammals", legs=2, extinct=False)
        self.client.add_and_flush(human)
        self.assertIsNotNone(human.id)

        # Check the entry is in the database
        retrieved_human = self.client.query_first(Species, name="human")
        self.assertEqual(human, retrieved_human)

        # Add an entry using 'insert_into_table'
        diplodocus = self.client.insert_into_table(Species, name="diplodocus", clade="dinosaurs", legs=4, extinct=True)
        self.assertTrue(isinstance(diplodocus, Species))
        self.assertEqual(diplodocus.name, "diplodocus")

        # Check that there are now 2 entries in the table
        full_table = self.client.query_all(Species)
        self.assertEqual(len(full_table), 2)

        # Try to insert the same entry again using find_or_insert
        result = self.client.find_or_insert(Species, name=diplodocus.name)
        self.assertEqual(result, diplodocus)

        # Insert another entry using find_or_insert
        bumblebee = self.client.find_or_insert(Species, name="bumblebee", clade="insects", legs=6, extinct=False)
        self.assertTrue(isinstance(bumblebee, Species))
        self.assertEqual(bumblebee.clade, "insects")

        # Check that there are now 2 entries in the table
        full_table = self.client.query_all(Species)
        self.assertEqual(len(full_table), 3)


class TestChadoClient(unittest.TestCase):
    """Test functions for loading data into a CHADO database"""

    connection_parameters = utils.parse_yaml(dbutils.default_configuration_file())
    connection_uri = dbutils.random_database_uri(connection_parameters)

    @classmethod
    def setUpClass(cls):
        # Creates a database, establishes a connection, creates tables and populates them with essential entries
        dbutils.create_database(cls.connection_uri)
        schema_base = base.PublicBase
        schema_metadata = schema_base.metadata
        essentials_client = essentials.EssentialsClient(cls.connection_uri)
        schema_metadata.create_all(essentials_client.engine, tables=schema_metadata.sorted_tables)
        essentials_client.load()
        cls.client = iobase.ChadoClient(cls.connection_uri)

    @classmethod
    def tearDownClass(cls):
        # Drops the database
        dbutils.drop_database(cls.connection_uri, True)

    def setUp(self):
        # Inserts default entries into database tables
        (self.default_db, self.default_dbxref, self.default_cv, self.default_cvterm, self.default_organism,
         self.default_feature, self.default_pub, self.default_synonym) = self.insert_default_entries()

    def tearDown(self):
        # Rolls back all changes to the database
        self.client.session.rollback()

    def test_query_feature_relationship_by_type(self):
        # Tests the function that creates a query against the feature_relationship table
        query = self.client.query_feature_relationship_by_type(12, [300, 400])
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("FROM public.feature_relationship", compiled_query)
        self.assertIn("feature_relationship.subject_id = 12", compiled_query)
        self.assertIn("feature_relationship.type_id IN (300, 400)", compiled_query)

    def test_query_featureprop_by_type(self):
        # Tests the function that creates a query against the feature_relationship table
        query = self.client.query_featureprop_by_type(12, [300, 400])
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("FROM public.featureprop", compiled_query)
        self.assertIn("featureprop.feature_id = 12", compiled_query)
        self.assertIn("featureprop.type_id IN (300, 400)", compiled_query)

    def test_query_feature_synonym_by_type(self):
        # Tests the function that creates a query against the feature_synonym table
        query = self.client.query_feature_synonym_by_type(12, [300, 400])
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("FROM public.feature_synonym JOIN public.synonym ON public.synonym.synonym_id = "
                      "public.feature_synonym.synonym_id", compiled_query)
        self.assertIn("feature_synonym.feature_id = 12", compiled_query)
        self.assertIn("synonym.type_id IN (300, 400)", compiled_query)

    def test_query_feature_cvterm_by_ontology(self):
        # Tests the function that creates a query against the feature_cvterm table
        query = self.client.query_feature_cvterm_by_ontology(12, 300)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("FROM public.feature_cvterm JOIN public.cvterm ON public.cvterm.cvterm_id = "
                      "public.feature_cvterm.cvterm_id JOIN public.dbxref ON public.dbxref.dbxref_id = "
                      "public.cvterm.dbxref_id", compiled_query)
        self.assertIn("feature_cvterm.feature_id = 12", compiled_query)
        self.assertIn("dbxref.db_id = 300", compiled_query)

    def test_query_feature_cvterm_by_ontology_and_organism(self):
        # Tests the function that creates a query against the feature_cvterm table
        query = self.client.query_feature_cvterm_by_ontology_and_organism(12, 300)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("FROM public.feature_cvterm JOIN public.feature ON public.feature.feature_id = "
                      "public.feature_cvterm.feature_id JOIN public.cvterm ON public.cvterm.cvterm_id = "
                      "public.feature_cvterm.cvterm_id JOIN public.dbxref ON public.dbxref.dbxref_id = "
                      "public.cvterm.dbxref_id", compiled_query)
        self.assertIn("feature.organism_id = 12", compiled_query)
        self.assertIn("dbxref.db_id = 300", compiled_query)

    def test_query_parent_features(self):
        # Tests the function that creates a query against the feature_relationship table
        query = self.client.query_parent_features(12, [300, 400])
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("FROM public.feature_relationship JOIN public.feature "
                      "ON public.feature.feature_id = public.feature_relationship.object_id",
                      compiled_query)
        self.assertIn("public.feature_relationship.subject_id = 12", compiled_query)
        self.assertIn("public.feature_relationship.type_id IN (300, 400)", compiled_query)

    def test_query_child_features(self):
        # Tests the function that creates a query against the feature_relationship table
        query = self.client.query_child_features(12, 300)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("FROM public.feature_relationship JOIN public.feature "
                      "ON public.feature.feature_id = public.feature_relationship.subject_id",
                      compiled_query)
        self.assertIn("public.feature_relationship.object_id = 12", compiled_query)
        self.assertIn("public.feature_relationship.type_id = 300", compiled_query)

    def test_query_features_by_srcfeature(self):
        # Tests the function that creates a query against the featureloc table
        query = self.client.query_features_by_srcfeature(12)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("FROM public.featureloc JOIN public.feature "
                      "ON public.feature.feature_id = public.featureloc.feature_id", compiled_query)
        self.assertIn("public.featureloc.srcfeature_id = 12", compiled_query)

    def test_query_features_by_property_type(self):
        # Tests the function that creates a query against the feature table
        query = self.client.query_features_by_property_type(12, 300)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("FROM public.featureprop JOIN public.feature "
                      "ON public.feature.feature_id = public.featureprop.feature_id", compiled_query)
        self.assertIn("public.feature.organism_id = 12", compiled_query)
        self.assertIn("public.featureprop.type_id = 300", compiled_query)

    def test_query_features_by_type(self):
        # Tests the function that creates a query against the feature table
        query = self.client.query_features_by_type(12, [300, 400])
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("FROM public.feature", compiled_query)
        self.assertIn("public.feature.organism_id = 12", compiled_query)
        self.assertIn("public.feature.type_id IN (300, 400)", compiled_query)

    def test_query_protein_features(self):
        # Tests the function that creates a query against the feature table
        query = self.client.query_protein_features(12, 222, 55, 66)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("FROM public.feature AS protein_feature "
                      "JOIN public.feature_relationship AS protein_transcript_relationship "
                      "ON protein_transcript_relationship.subject_id = protein_feature.feature_id "
                      "JOIN public.feature AS transcript_feature "
                      "ON transcript_feature.feature_id = protein_transcript_relationship.object_id "
                      "JOIN public.feature_relationship AS transcript_gene_relationship "
                      "ON transcript_gene_relationship.subject_id = transcript_feature.feature_id "
                      "JOIN public.feature AS gene_feature "
                      "ON gene_feature.feature_id = transcript_gene_relationship.object_id", compiled_query)
        self.assertIn("protein_feature.organism_id = 12", compiled_query)
        self.assertIn("protein_transcript_relationship.type_id = 66", compiled_query)
        self.assertIn("transcript_gene_relationship.type_id = 55", compiled_query)
        self.assertIn("gene_feature.type_id = 222", compiled_query)

    def test_query_feature_properties(self):
        # Tests the function that creates a query against the featureprop and cvterm tables
        query = self.client.query_feature_properties(44)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("SELECT public.cvterm.name, public.featureprop.value", compiled_query)
        self.assertIn("FROM public.featureprop JOIN public.cvterm "
                      "ON public.cvterm.cvterm_id = public.featureprop.type_id", compiled_query)
        self.assertIn("WHERE public.featureprop.feature_id = 44", compiled_query)

    def test_query_feature_pubs(self):
        # Tests the function that creates a query against the feature_pub and pub tables
        query = self.client.query_feature_pubs(44)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("SELECT public.pub.uniquename", compiled_query)
        self.assertIn("FROM public.feature_pub JOIN public.pub "
                      "ON public.pub.pub_id = public.feature_pub.pub_id", compiled_query)
        self.assertIn("WHERE public.feature_pub.feature_id = 44", compiled_query)

    def test_query_feature_dbxrefs(self):
        # Tests the function that creates a query against the feature_dbxref, dxbref and db tables
        query = self.client.query_feature_dbxrefs(44)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("SELECT public.db.name, public.dbxref.accession", compiled_query)
        self.assertIn("FROM public.feature_dbxref JOIN public.dbxref "
                      "ON public.dbxref.dbxref_id = public.feature_dbxref.dbxref_id JOIN public.db "
                      "ON public.db.db_id = public.dbxref.db_id", compiled_query)
        self.assertIn("WHERE public.feature_dbxref.feature_id = 44", compiled_query)

    def test_query_feature_synonyms(self):
        # Tests the function that creates a query against the feature_synonym, synonym and cvterm tables
        query = self.client.query_feature_synonyms(44)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("SELECT public.cvterm.name AS type, public.synonym.name AS synonym", compiled_query)
        self.assertIn("FROM public.feature_synonym JOIN public.synonym "
                      "ON public.synonym.synonym_id = public.feature_synonym.synonym_id JOIN public.cvterm "
                      "ON public.cvterm.cvterm_id = public.synonym.type_id", compiled_query)
        self.assertIn("WHERE public.feature_synonym.feature_id = 44", compiled_query)

    def test_query_feature_ontology_terms(self):
        # Tests the function that creates a query against the feature_cvterm, cvterm, dxbref and db tables
        query = self.client.query_feature_ontology_terms(44, 81)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("SELECT public.db.name, public.dbxref.accession", compiled_query)
        self.assertIn("FROM public.feature_cvterm JOIN public.cvterm "
                      "ON public.cvterm.cvterm_id = public.feature_cvterm.cvterm_id JOIN public.dbxref "
                      "ON public.dbxref.dbxref_id = public.cvterm.dbxref_id JOIN public.db "
                      "ON public.db.db_id = public.dbxref.db_id", compiled_query)
        self.assertIn("WHERE public.feature_cvterm.feature_id = 44 AND public.db.db_id = 81", compiled_query)

    def test_query_feature_cvterm_properties(self):
        # Tests the function that creates a query against the feature_cvtermprop table
        query = self.client.query_feature_cvterm_properties(44)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("SELECT public.cvterm.name, public.feature_cvtermprop.value", compiled_query)
        self.assertIn("FROM public.feature_cvtermprop JOIN public.cvterm "
                      "ON public.cvterm.cvterm_id = public.feature_cvtermprop.type_id", compiled_query)
        self.assertIn("WHERE public.feature_cvtermprop.feature_cvterm_id = 44", compiled_query)

    def test_query_feature_cvterm_pubs(self):
        # Tests the function that creates a query against the feature_cvterm and pub tables
        query = self.client.query_feature_cvterm_pubs(44)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("SELECT public.pub.uniquename", compiled_query)
        self.assertIn("FROM public.feature_cvterm JOIN public.pub "
                      "ON public.pub.pub_id = public.feature_cvterm.pub_id", compiled_query)
        self.assertIn("WHERE public.feature_cvterm.feature_cvterm_id = 44", compiled_query)

    def test_query_feature_cvterm_secondary_pubs(self):
        # Tests the function that creates a query against the feature_cvterm_pub and pub tables
        query = self.client.query_feature_cvterm_secondary_pubs(44)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("SELECT public.pub.uniquename", compiled_query)
        self.assertIn("FROM public.feature_cvterm_pub JOIN public.pub "
                      "ON public.pub.pub_id = public.feature_cvterm_pub.pub_id", compiled_query)
        self.assertIn("WHERE public.feature_cvterm_pub.feature_cvterm_id = 44", compiled_query)

    def test_query_feature_cvterm_dbxrefs(self):
        # Tests the function that creates a query against the feature_cvterm_dbxref, dxbref and db tables
        query = self.client.query_feature_cvterm_dbxrefs(44)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("SELECT public.db.name, public.dbxref.accession", compiled_query)
        self.assertIn("FROM public.feature_cvterm_dbxref JOIN public.dbxref "
                      "ON public.dbxref.dbxref_id = public.feature_cvterm_dbxref.dbxref_id JOIN public.db "
                      "ON public.db.db_id = public.dbxref.db_id", compiled_query)
        self.assertIn("WHERE public.feature_cvterm_dbxref.feature_cvterm_id = 44", compiled_query)

    def test_query_feature_cvterm_ontology_terms(self):
        # Tests the function that creates a query against the feature_cvterm, cvterm, dxbref and db tables
        query = self.client.query_feature_cvterm_ontology_terms(44, 81)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("SELECT public.db.name, public.dbxref.accession", compiled_query)
        self.assertIn("FROM public.feature_cvterm JOIN public.cvterm "
                      "ON public.cvterm.cvterm_id = public.feature_cvterm.cvterm_id JOIN public.dbxref "
                      "ON public.dbxref.dbxref_id = public.cvterm.dbxref_id JOIN public.db "
                      "ON public.db.db_id = public.dbxref.db_id", compiled_query)
        self.assertIn("WHERE public.feature_cvterm.feature_cvterm_id = 44 AND public.db.db_id = 81", compiled_query)

    def test_query_cvterm_namespace(self):
        # Tests the function that creates a query against the cvterm and cv tables
        query = self.client.query_cvterm_namespace(44)
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("SELECT public.cv.name", compiled_query)
        self.assertIn("FROM public.cvterm JOIN public.cv ON public.cv.cv_id = public.cvterm.cv_id", compiled_query)
        self.assertIn("WHERE public.cvterm.cvterm_id = 44", compiled_query)

    def insert_default_entries(self):
        # Inserts CV terms needed as basis for virtually all tests
        default_db = general.Db(name="defaultdb")
        self.client.add_and_flush(default_db)
        default_dbxref = general.DbxRef(db_id=default_db.db_id, accession="defaultaccession")
        self.client.add_and_flush(default_dbxref)
        default_cv = cv.Cv(name="defaultcv")
        self.client.add_and_flush(default_cv)
        default_cvterm = cv.CvTerm(cv_id=default_cv.cv_id, dbxref_id=default_dbxref.dbxref_id, name="defaultterm")
        self.client.add_and_flush(default_cvterm)
        default_organism = organism.Organism(genus="defaultgenus", species="defaultspecies", abbreviation="defaultorg")
        self.client.add_and_flush(default_organism)
        default_feature = sequence.Feature(organism_id=default_organism.organism_id, type_id=default_cvterm.cvterm_id,
                                           uniquename="defaultfeature")
        self.client.add_and_flush(default_feature)
        default_pub = pub.Pub(uniquename="defaultpub", type_id=default_cvterm.cvterm_id)
        self.client.add_and_flush(default_pub)
        default_synonym = sequence.Synonym(name="defaultsynonym", type_id=default_cvterm.cvterm_id, synonym_sgml="")
        self.client.add_and_flush(default_synonym)
        return (default_db, default_dbxref, default_cv, default_cvterm, default_organism, default_feature, default_pub,
                default_synonym)

    def test_load_db(self):
        # Tests the function loading a DB entry from the database
        db_entry = self.client._load_db("defaultdb")
        self.assertEqual("defaultdb", db_entry.name)
        with self.assertRaises(iobase.DatabaseError):
            self.client._load_db("inexistent_db")

    def test_load_dbs(self):
        # Tests the function loading multiple DB entries from the database
        db_entries = self.client._load_dbs(["defaultdb"])
        self.assertEqual(len(db_entries), 1)

    def test_load_cvterm(self):
        # Tests the function loading a CV term from the database
        comment_term = self.client._load_cvterm("comment")
        self.assertEqual("comment", comment_term.name)
        with self.assertRaises(iobase.DatabaseError):
            self.client._load_cvterm("inexistent_term")

    def test_load_cvterm_from_cv(self):
        # Tests the function loading a CV term from the database
        existent_term = self.client._load_cvterm_from_cv("defaultterm", "defaultcv")
        self.assertEqual("defaultterm", existent_term.name)
        with self.assertRaises(iobase.DatabaseError):
            self.client._load_cvterm_from_cv("wrong_term", "defaultcv")
        with self.assertRaises(iobase.DatabaseError):
            self.client._load_cvterm_from_cv("defaultterm", "wrong_cv")

    def test_load_cvterms(self):
        # Tests the function loading multiple CV terms from the database
        synonym_type_terms = self.client._load_cvterms(["narrow", "broad"])
        self.assertEqual(len(synonym_type_terms), 2)
        self.assertEqual("narrow", synonym_type_terms[0].name)

    def test_load_terms_from_cv(self):
        # Tests the function loading multiple CV terms from the database
        synonym_type_terms = self.client._load_terms_from_cv("synonym_type", False)
        self.assertGreater(len(synonym_type_terms), 0)
        synonym_type_terms = self.client._load_terms_from_cv("synonym_type", True)
        self.assertEqual(len(synonym_type_terms), 0)
        with self.assertRaises(iobase.DatabaseError):
            self.client._load_terms_from_cv("inexistent_vocabulary")

    def test_load_terms_from_cv_dict(self):
        # Tests the function loading multiple CV terms from the database
        synonym_type_terms = self.client._load_terms_from_cv_dict("synonym_type", ["narrow", "broad"], False)
        self.assertIn("narrow", synonym_type_terms)
        self.assertEqual(synonym_type_terms["narrow"].name, "narrow")
        with self.assertRaises(iobase.DatabaseError):
            self.client._load_terms_from_cv_dict("synonym_type", ["inexistent_term"], False)

    def test_extract_cvterm_ids_from_dict(self):
        # Tests the function that extracts the IDs of CV terms in a dictionary
        cvterm_dict = {"testterm": cv.CvTerm(cvterm_id=22, cv_id=1, dbxref_id=2, name="testterm")}
        cvterm_ids = self.client._extract_cvterm_ids_from_dict(cvterm_dict, ["testterm"])
        self.assertEqual(cvterm_ids, [22])
        with self.assertRaises(iobase.DatabaseError):
            self.client._extract_cvterm_ids_from_dict(cvterm_dict, ["otherterm"])

    def test_load_organism(self):
        # Tests the function loading an organism from the database
        with self.assertRaises(iobase.DatabaseError):
            self.client._load_organism("testorganism")
        testclient = direct.DirectIOClient(self.connection_uri)
        testclient.insert_organism(genus="testgenus", species="testspecies", abbreviation="testorganism")
        testorganism = self.client._load_organism("testorganism")
        self.assertEqual(testorganism.species, "testspecies")

    def test_load_pub(self):
        # Tests the function loading a publication from the database
        testpub = self.client._load_pub("null")
        self.assertEqual("null", testpub.uniquename)
        with self.assertRaises(iobase.DatabaseError):
            self.client._load_pub("inexistent_pub")

    def test_load_feature_ids(self):
        # Tests the function loading all existing IDs of features from a database
        feature_entry = sequence.Feature(organism_id=self.default_organism.organism_id,
                                         type_id=self.default_cvterm.cvterm_id, uniquename="testname")
        self.client.add_and_flush(feature_entry)
        all_uniquenames = self.client._load_feature_names(self.default_organism)
        self.assertIn("testname", all_uniquenames)

    def test_handle_organism(self):
        # Tests the function importing an organism to the database
        # Insert an organism and check this is successful
        new_entry = organism.Organism(genus="testgenus", species="testspecies", infraspecific_name="teststrain",
                                      abbreviation="testabbreviation", common_name="testname", comment="testcomment")
        first_entry = self.client._handle_organism(new_entry)
        self.assertIsNotNone(first_entry.organism_id)
        self.assertEqual(first_entry.common_name, "testname")

        # Try to insert an organism with the same genus/species/strain, but different abbreviation,
        # and check that nothing changes
        another_entry = organism.Organism(genus="testgenus", species="testspecies", infraspecific_name="teststrain",
                                          abbreviation="otherabbreviation", common_name="othername")
        second_entry = self.client._handle_organism(another_entry)
        self.assertIs(second_entry, first_entry)
        self.assertEqual(second_entry.common_name, "testname")

        # Try to insert an organism with the different genus/species/strain, but same abbreviation,
        # and check that nothing changes
        yet_another_entry = organism.Organism(genus="othergenus", species="otherspecies", common_name="othername",
                                              infraspecific_name="otherstrain", abbreviation="testabbreviation")
        third_entry = self.client._handle_organism(yet_another_entry)
        self.assertIs(third_entry, first_entry)
        self.assertEqual(third_entry.common_name, "testname")

        # Try to insert an organism with same genus/species/strain and abbreviation, and check that this updates the
        # additional properties
        another_entry.abbreviation = "testabbreviation"
        fourth_entry = self.client._handle_organism(another_entry)
        self.assertIs(fourth_entry, first_entry)
        self.assertEqual(fourth_entry.common_name, "othername")

    def test_delete_organism(self):
        # Tests the function deleting an organism from the database
        existing_entry = organism.Organism(genus="testgenus", species="testspecies", infraspecific_name="teststrain",
                                           abbreviation="testabbreviation", common_name="testname")
        self.client.add_and_flush(existing_entry)
        all_entries = self.client.query_all(organism.Organism)
        self.assertIn(existing_entry, all_entries)

        deleted_entries = self.client._delete_organism("inexistent_abbreviation")
        self.assertEqual(len(deleted_entries), 0)

        deleted_entries = self.client._delete_organism("testabbreviation")
        self.assertEqual(len(deleted_entries), 1)
        self.assertIn(existing_entry, deleted_entries)
        all_entries = self.client.query_all(organism.Organism)
        self.assertNotIn(existing_entry, all_entries)

    def test_handle_organismprop(self):
        # Tests the function importing an organism property to the database
        new_entry = organism.OrganismProp(organism_id=self.default_organism.organism_id,
                                          type_id=self.default_cvterm.cvterm_id, value="testvalue")
        first_entry = self.client._handle_organismprop(new_entry)
        self.assertIsNotNone(first_entry.organismprop_id)
        self.assertEqual(first_entry.value, "testvalue")

        another_entry = organism.OrganismProp(organism_id=self.default_organism.organism_id,
                                              type_id=self.default_cvterm.cvterm_id, value="othervalue")
        second_entry = self.client._handle_organismprop(another_entry)
        self.assertIs(second_entry, first_entry)
        self.assertEqual(second_entry.value, "othervalue")

    def test_handle_organism_dbxref(self):
        # Tests the function importing a db cross reference for an organism to the database
        new_entry = organism.OrganismDbxRef(organism_id=self.default_organism.organism_id,
                                            dbxref_id=self.default_dbxref.dbxref_id)
        first_entry = self.client._handle_organism_dbxref(new_entry)
        self.assertIsNotNone(first_entry.organism_dbxref_id)

        other_dbxref = general.DbxRef(db_id=self.default_db.db_id, accession="otheraccession")
        self.client.add_and_flush(other_dbxref)
        another_entry = organism.OrganismDbxRef(organism_id=self.default_organism.organism_id,
                                                dbxref_id=other_dbxref.dbxref_id)
        second_entry = self.client._handle_organism_dbxref(another_entry)
        self.assertIsNot(second_entry, first_entry)

    def test_handle_db(self):
        # Tests the function importing a db to the database
        new_entry = general.Db(name="testname")
        first_entry = self.client._handle_db(new_entry)
        self.assertIsNotNone(first_entry.db_id)
        self.assertEqual(first_entry.name, "testname")

        another_entry = general.Db(name="testname")
        second_entry = self.client._handle_db(another_entry)
        self.assertIs(second_entry, first_entry)

    def test_handle_dbxref(self):
        # Tests the function importing a db cross reference to the database
        new_entry = general.DbxRef(db_id=self.default_db.db_id, accession="testaccession", version="testversion")
        first_entry = self.client._handle_dbxref(new_entry)
        self.assertIsNotNone(first_entry.dbxref_id)
        self.assertEqual(first_entry.accession, "testaccession")

        another_entry = general.DbxRef(db_id=self.default_db.db_id, accession="testaccession", version="testversion")
        second_entry = self.client._handle_dbxref(another_entry)
        self.assertIs(second_entry, first_entry)

        another_entry.accession = "otheraccession"
        third_entry = self.client._handle_dbxref(another_entry)
        self.assertIsNot(third_entry, first_entry)
        self.assertEqual(third_entry.accession, "otheraccession")

    def test_handle_cv(self):
        # Tests the function importing a controlled vocabulary to the database
        new_entry = cv.Cv(name="testname")
        first_entry = self.client._handle_cv(new_entry)
        self.assertIsNotNone(first_entry.cv_id)
        self.assertEqual(first_entry.name, "testname")

        another_entry = cv.Cv(name="testname")
        second_entry = self.client._handle_cv(another_entry)
        self.assertIs(second_entry, first_entry)

    def test_handle_cvterm(self):
        # Tests the function importing a term of a controlled vocabulary to the database
        # Insert a CV term
        test_dbxref = general.DbxRef(db_id=self.default_db.db_id, accession="testaccession")
        self.client.add_and_flush(test_dbxref)
        new_entry = cv.CvTerm(cv_id=self.default_cv.cv_id, name="testname", dbxref_id=test_dbxref.dbxref_id)
        first_entry = self.client._handle_cvterm(new_entry)
        self.assertIsNotNone(first_entry.cvterm_id)
        self.assertEqual(first_entry.name, "testname")

        # Try to insert another CV term with same cv_id/name, and check that the previously inserted entry is returned
        other_dbxref = general.DbxRef(db_id=self.default_db.db_id, accession="otheraccession")
        self.client.add_and_flush(other_dbxref)
        another_entry = cv.CvTerm(cv_id=self.default_cv.cv_id, name="testname", dbxref_id=other_dbxref.dbxref_id)
        second_entry = self.client._handle_cvterm(another_entry)
        self.assertIs(second_entry, first_entry)

        # Try to insert another CV term with same dbxref, and check that the previously inserted entry is returned
        other_cv = cv.Cv(name="othervocabulary")
        self.client.add_and_flush(other_cv)
        yet_another_entry = cv.CvTerm(cv_id=other_cv.cv_id, name="testname", dbxref_id=test_dbxref.dbxref_id)
        third_entry = self.client._handle_cvterm(yet_another_entry)
        self.assertIs(third_entry, first_entry)

        # Try to insert another CV term with different dbxref and different name, and check that this succeeds
        another_entry.name = "othername"
        fourth_entry = self.client._handle_cvterm(another_entry)
        self.assertIsNot(fourth_entry, first_entry)
        self.assertEqual(fourth_entry.name, "othername")

    def test_handle_feature(self):
        # Tests the function importing a feature to the database
        new_entry = sequence.Feature(organism_id=self.default_organism.organism_id,
                                     type_id=self.default_cvterm.cvterm_id, uniquename="testname", name="name1")
        first_entry = self.client._handle_feature(new_entry)
        self.assertIs(first_entry, new_entry)
        self.assertEqual(first_entry.uniquename, "testname")
        self.assertEqual(first_entry.name, "name1")

        another_entry = sequence.Feature(organism_id=self.default_organism.organism_id,
                                         type_id=self.default_cvterm.cvterm_id, uniquename="testname", name="name2")
        second_entry = self.client._handle_feature(another_entry)
        self.assertIs(second_entry, new_entry)
        self.assertIsNot(second_entry, another_entry)
        self.assertEqual(second_entry.name, "name2")

        yet_another_entry = sequence.Feature(organism_id=self.default_organism.organism_id,
                                             type_id=self.default_cvterm.cvterm_id, uniquename="othername")
        third_entry = self.client._handle_feature(yet_another_entry)
        self.assertIsNot(third_entry, new_entry)
        self.assertIs(third_entry, yet_another_entry)
        self.assertEqual(third_entry.uniquename, "othername")

    def test_handle_featureloc(self):
        # Tests the function importing a featureloc to the database
        other_feature = sequence.Feature(organism_id=self.default_organism.organism_id,
                                         type_id=self.default_cvterm.cvterm_id, uniquename="othername")
        self.client.add_and_flush(other_feature)
        new_entry = sequence.FeatureLoc(feature_id=self.default_feature.feature_id,
                                        srcfeature_id=other_feature.feature_id, strand=1)
        first_entry = self.client._handle_featureloc(new_entry)
        self.assertIs(first_entry, new_entry)
        self.assertEqual(first_entry.strand, 1)

        another_entry = sequence.FeatureLoc(feature_id=self.default_feature.feature_id,
                                            srcfeature_id=other_feature.feature_id, strand=-1)
        second_entry = self.client._handle_featureloc(another_entry)
        self.assertIs(second_entry, new_entry)
        self.assertIsNot(second_entry, another_entry)
        self.assertEqual(second_entry.strand, -1)

    def test_handle_featureprop(self):
        # Tests the function importing a featureprop to the database
        new_entry = sequence.FeatureProp(feature_id=self.default_feature.feature_id,
                                         type_id=self.default_cvterm.cvterm_id, value="testvalue")
        first_entry = self.client._handle_featureprop(new_entry, [])
        self.assertIs(first_entry, new_entry)
        self.assertEqual(first_entry.rank, 0)

        another_entry = sequence.FeatureProp(feature_id=self.default_feature.feature_id,
                                             type_id=self.default_cvterm.cvterm_id, value="testvalue")
        existing_entries = self.client.query_all(sequence.FeatureProp, feature_id=new_entry.feature_id)
        second_entry = self.client._handle_featureprop(another_entry, existing_entries)
        self.assertIs(second_entry, new_entry)
        self.assertIsNot(second_entry, another_entry)

        yet_another_entry = sequence.FeatureProp(feature_id=self.default_feature.feature_id,
                                                 type_id=self.default_cvterm.cvterm_id, value="othervalue")
        third_entry = self.client._handle_featureprop(yet_another_entry, existing_entries)
        self.assertIsNot(third_entry, new_entry)
        self.assertIs(third_entry, yet_another_entry)
        self.assertEqual(third_entry.rank, 1)

    def test_delete_featureprop(self):
        # Tests the function deleting a featureprop from the database
        existing_entry = sequence.FeatureProp(feature_id=self.default_feature.feature_id,
                                              type_id=self.default_cvterm.cvterm_id, value="testvalue")
        self.client.add_and_flush(existing_entry)
        all_entries = self.client.query_all(sequence.FeatureProp)
        self.assertIn(existing_entry, all_entries)

        deleted_entries = self.client._delete_featureprop([], [existing_entry])
        self.assertEqual(len(deleted_entries), 1)
        self.assertIn(existing_entry, deleted_entries)
        all_entries = self.client.query_all(sequence.FeatureProp)
        self.assertNotIn(existing_entry, all_entries)

    def test_handle_feature_dbxref(self):
        # Tests the function importing a feature_dbxref to the database
        new_entry = sequence.FeatureDbxRef(feature_id=self.default_feature.feature_id,
                                           dbxref_id=self.default_dbxref.dbxref_id, is_current=True)
        first_entry = self.client._handle_feature_dbxref(new_entry, [])
        self.assertIs(first_entry, new_entry)
        self.assertTrue(first_entry.is_current)

        another_entry = sequence.FeatureDbxRef(feature_id=self.default_feature.feature_id,
                                               dbxref_id=self.default_dbxref.dbxref_id, is_current=False)
        existing_entries = self.client.query_all(sequence.FeatureDbxRef, feature_id=new_entry.feature_id)
        second_entry = self.client._handle_feature_dbxref(another_entry, existing_entries)
        self.assertIs(second_entry, new_entry)
        self.assertIsNot(second_entry, another_entry)
        self.assertFalse(second_entry.is_current)

    def test_delete_feature_dbxref(self):
        # Tests the function deleting a feature_dbxref from the database
        existing_entry = sequence.FeatureDbxRef(feature_id=self.default_feature.feature_id,
                                                dbxref_id=self.default_dbxref.dbxref_id)
        self.client.add_and_flush(existing_entry)
        all_entries = self.client.query_all(sequence.FeatureDbxRef)
        self.assertIn(existing_entry, all_entries)

        deleted_entries = self.client._delete_feature_dbxref([], [existing_entry])
        self.assertEqual(len(deleted_entries), 1)
        self.assertIn(existing_entry, deleted_entries)
        all_entries = self.client.query_all(sequence.FeatureDbxRef)
        self.assertNotIn(existing_entry, all_entries)

    def test_handle_feature_cvterm(self):
        # Tests the function importing a feature_cvterm to the database
        new_entry = sequence.FeatureCvTerm(feature_id=self.default_feature.feature_id,
                                           cvterm_id=self.default_cvterm.cvterm_id, pub_id=self.default_pub.pub_id)
        first_entry = self.client._handle_feature_cvterm(new_entry, [])
        self.assertIs(first_entry, new_entry)
        self.assertFalse(first_entry.is_not)

        another_entry = sequence.FeatureCvTerm(feature_id=self.default_feature.feature_id,
                                               cvterm_id=self.default_cvterm.cvterm_id, pub_id=self.default_pub.pub_id,
                                               is_not=True)
        existing_entries = self.client.query_all(sequence.FeatureCvTerm, feature_id=new_entry.feature_id)
        second_entry = self.client._handle_feature_cvterm(another_entry, existing_entries)
        self.assertIs(second_entry, new_entry)
        self.assertIsNot(second_entry, another_entry)
        self.assertTrue(second_entry.is_not)

    def test_delete_feature_cvterm(self):
        # Tests the function deleting a feature_cvterm from the database
        existing_entry = sequence.FeatureCvTerm(feature_id=self.default_feature.feature_id,
                                                cvterm_id=self.default_cvterm.cvterm_id, pub_id=self.default_pub.pub_id)
        self.client.add_and_flush(existing_entry)
        all_entries = self.client.query_all(sequence.FeatureCvTerm)
        self.assertIn(existing_entry, all_entries)

        deleted_entries = self.client._delete_feature_cvterm([], [existing_entry])
        self.assertEqual(len(deleted_entries), 1)
        self.assertIn(existing_entry, deleted_entries)
        all_entries = self.client.query_all(sequence.FeatureCvTerm)
        self.assertNotIn(existing_entry, all_entries)

    def test_handle_feature_relationship(self):
        # Tests the function importing a feature_relationship to the database
        other_feature = sequence.Feature(organism_id=self.default_organism.organism_id,
                                         type_id=self.default_cvterm.cvterm_id, uniquename="otherfeature")
        self.client.add_and_flush(other_feature)
        new_entry = sequence.FeatureRelationship(subject_id=self.default_feature.feature_id,
                                                 object_id=other_feature.feature_id,
                                                 type_id=self.default_cvterm.cvterm_id, value="testvalue")
        first_entry = self.client._handle_feature_relationship(new_entry, [])
        self.assertIs(first_entry, new_entry)
        self.assertEqual(first_entry.value, "testvalue")

        another_entry = sequence.FeatureRelationship(subject_id=self.default_feature.feature_id,
                                                     object_id=other_feature.feature_id,
                                                     type_id=self.default_cvterm.cvterm_id, value="othervalue")
        existing_entries = self.client.query_all(sequence.FeatureRelationship, subject_id=new_entry.subject_id)
        second_entry = self.client._handle_feature_relationship(another_entry, existing_entries)
        self.assertIs(second_entry, new_entry)
        self.assertIsNot(second_entry, another_entry)
        self.assertEqual(second_entry.value, "othervalue")

    def test_delete_feature_relationship(self):
        # Tests the function deleting a feature_relationship from the database
        other_feature = sequence.Feature(organism_id=self.default_organism.organism_id,
                                         type_id=self.default_cvterm.cvterm_id, uniquename="otherfeature")
        self.client.add_and_flush(other_feature)
        existing_entry = sequence.FeatureRelationship(subject_id=self.default_feature.feature_id,
                                                      object_id=other_feature.feature_id,
                                                      type_id=self.default_cvterm.cvterm_id)
        self.client.add_and_flush(existing_entry)
        all_entries = self.client.query_all(sequence.FeatureRelationship)
        self.assertIn(existing_entry, all_entries)

        deleted_entries = self.client._delete_feature_relationship([], [existing_entry])
        self.assertEqual(len(deleted_entries), 1)
        self.assertIn(existing_entry, deleted_entries)
        all_entries = self.client.query_all(sequence.FeatureRelationship)
        self.assertNotIn(existing_entry, all_entries)

    def test_handle_synonym(self):
        # Tests the function importing a synonym to the database
        new_entry = sequence.Synonym(name="testname", type_id=self.default_cvterm.cvterm_id, synonym_sgml="testsgml")
        first_entry = self.client._handle_synonym(new_entry)
        self.assertIs(first_entry, new_entry)
        self.assertEqual(first_entry.synonym_sgml, "testsgml")

        another_entry = sequence.Synonym(name="testname", type_id=self.default_cvterm.cvterm_id, synonym_sgml="sgml")
        second_entry = self.client._handle_synonym(another_entry)
        self.assertIs(second_entry, first_entry)
        self.assertEqual(second_entry.synonym_sgml, "sgml")

    def test_handle_feature_synonym(self):
        # Tests the function importing a feature_synonym to the database
        new_entry = sequence.FeatureSynonym(synonym_id=self.default_synonym.synonym_id,
                                            feature_id=self.default_feature.feature_id,
                                            pub_id=self.default_pub.pub_id, is_current=True)
        first_entry = self.client._handle_feature_synonym(new_entry, [])
        self.assertIs(first_entry, new_entry)
        self.assertTrue(first_entry.is_current)

        another_entry = sequence.FeatureSynonym(synonym_id=self.default_synonym.synonym_id,
                                                feature_id=self.default_feature.feature_id,
                                                pub_id=self.default_pub.pub_id, is_current=False)
        existing_entries = self.client.query_all(sequence.FeatureSynonym, feature_id=new_entry.feature_id)
        second_entry = self.client._handle_feature_synonym(another_entry, existing_entries)
        self.assertIs(second_entry, new_entry)
        self.assertIsNot(second_entry, another_entry)
        self.assertFalse(second_entry.is_current)

    def test_delete_feature_synonym(self):
        # Tests the function deleting a feature_synonym from the database
        existing_entry = sequence.FeatureSynonym(feature_id=self.default_feature.feature_id,
                                                 synonym_id=self.default_synonym.synonym_id,
                                                 pub_id=self.default_pub.pub_id)
        self.client.add_and_flush(existing_entry)
        all_entries = self.client.query_all(sequence.FeatureSynonym)
        self.assertIn(existing_entry, all_entries)

        deleted_entries = self.client._delete_feature_synonym([], [existing_entry])
        self.assertEqual(len(deleted_entries), 1)
        self.assertIn(existing_entry, deleted_entries)
        all_entries = self.client.query_all(sequence.FeatureSynonym)
        self.assertNotIn(existing_entry, all_entries)

    def test_handle_pub(self):
        # Tests the function importing a publication to the database
        new_entry = pub.Pub(uniquename="testname", type_id=self.default_cvterm.cvterm_id, volume="testvolume")
        first_entry = self.client._handle_pub(new_entry)
        self.assertIs(first_entry, new_entry)
        self.assertEqual(first_entry.volume, "testvolume")

        another_entry = pub.Pub(uniquename="testname", type_id=self.default_cvterm.cvterm_id, volume="othervolume")
        second_entry = self.client._handle_pub(another_entry)
        self.assertIs(second_entry, first_entry)
        self.assertEqual(second_entry.volume, "othervolume")

    def test_handle_featurepub(self):
        # Tests the function importing a feature_pub to the database
        new_entry = sequence.FeaturePub(feature_id=self.default_feature.feature_id, pub_id=self.default_pub.pub_id)
        first_entry = self.client._handle_feature_pub(new_entry, [])
        self.assertIs(first_entry, new_entry)

        another_entry = sequence.FeaturePub(feature_id=self.default_feature.feature_id, pub_id=self.default_pub.pub_id)
        existing_entries = self.client.query_all(sequence.FeaturePub, feature_id=new_entry.feature_id)
        second_entry = self.client._handle_feature_pub(another_entry, existing_entries)
        self.assertIs(second_entry, new_entry)
        self.assertIsNot(second_entry, another_entry)

    def test_delete_featurepub(self):
        # Tests the function deleting a feature_pub from the database
        existing_entry = sequence.FeaturePub(feature_id=self.default_feature.feature_id, pub_id=self.default_pub.pub_id)
        self.client.add_and_flush(existing_entry)
        all_entries = self.client.query_all(sequence.FeaturePub)
        self.assertIn(existing_entry, all_entries)

        deleted_entries = self.client._delete_feature_pub([], [existing_entry])
        self.assertEqual(len(deleted_entries), 1)
        self.assertIn(existing_entry, deleted_entries)
        all_entries = self.client.query_all(sequence.FeaturePub)
        self.assertNotIn(existing_entry, all_entries)

    def test_handle_feature_cvtermprop(self):
        # Tests the function importing a feature_cvtermprop to the database
        feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=self.default_feature.feature_id,
                                                      cvterm_id=self.default_cvterm.cvterm_id,
                                                      pub_id=self.default_pub.pub_id)
        self.client.add_and_flush(feature_cvterm_entry)
        new_entry = sequence.FeatureCvTermProp(feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id,
                                               type_id=self.default_cvterm.cvterm_id, value="testvalue")
        first_entry = self.client._handle_feature_cvtermprop(new_entry, [])
        self.assertIs(first_entry, new_entry)
        self.assertEqual(first_entry.value, "testvalue")

        another_entry = sequence.FeatureCvTermProp(feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id,
                                                   type_id=self.default_cvterm.cvterm_id, value="othervalue")
        existing_entries = self.client.query_all(sequence.FeatureCvTermProp,
                                                 feature_cvterm_id=new_entry.feature_cvterm_id)
        second_entry = self.client._handle_feature_cvtermprop(another_entry, existing_entries)
        self.assertIs(second_entry, first_entry)
        self.assertEqual(second_entry.value, "othervalue")

    def test_handle_feature_cvterm_dbxref(self):
        # Tests the function importing a feature_cvterm_dbxref to the database
        feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=self.default_feature.feature_id,
                                                      cvterm_id=self.default_cvterm.cvterm_id,
                                                      pub_id=self.default_pub.pub_id)
        self.client.add_and_flush(feature_cvterm_entry)
        new_entry = sequence.FeatureCvTermDbxRef(feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id,
                                                 dbxref_id=self.default_dbxref.dbxref_id)
        first_entry = self.client._handle_feature_cvterm_dbxref(new_entry, [])
        self.assertIs(first_entry, new_entry)

        another_entry = sequence.FeatureCvTermDbxRef(feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id,
                                                     dbxref_id=self.default_dbxref.dbxref_id)
        existing_entries = self.client.query_all(sequence.FeatureCvTermDbxRef,
                                                 feature_cvterm_id=new_entry.feature_cvterm_id)
        second_entry = self.client._handle_feature_cvterm_dbxref(another_entry, existing_entries)
        self.assertIs(second_entry, new_entry)
        self.assertIsNot(second_entry, another_entry)

    def test_handle_feature_cvterm_pub(self):
        # Tests the function importing a feature_cvterm_pub to the database
        pub_entry = pub.Pub(uniquename="otherpub", type_id=self.default_cvterm.cvterm_id)
        self.client.add_and_flush(pub_entry)
        feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=self.default_feature.feature_id,
                                                      cvterm_id=self.default_cvterm.cvterm_id,
                                                      pub_id=self.default_pub.pub_id)
        self.client.add_and_flush(feature_cvterm_entry)

        new_entry = sequence.FeatureCvTermPub(feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id,
                                              pub_id=pub_entry.pub_id)
        first_entry = self.client._handle_feature_cvterm_pub(new_entry, [])
        self.assertIs(first_entry, new_entry)

        another_entry = sequence.FeatureCvTermPub(feature_cvterm_id=feature_cvterm_entry.feature_cvterm_id,
                                                  pub_id=pub_entry.pub_id)
        existing_entries = self.client.query_all(sequence.FeatureCvTermPub,
                                                 feature_cvterm_id=new_entry.feature_cvterm_id)
        second_entry = self.client._handle_feature_cvterm_pub(another_entry, existing_entries)
        self.assertIs(second_entry, new_entry)
        self.assertIsNot(second_entry, another_entry)

    def test_mark_feature_as_obsolete(self):
        # Tests the function that marks a feature as obsolete
        feature = sequence.Feature(organism_id=self.default_organism.organism_id, type_id=self.default_cvterm.cvterm_id,
                                   uniquename="testname", is_obsolete=False)
        self.client.add_and_flush(feature)
        obsolete_feature = self.client._mark_feature_as_obsolete(self.default_organism, "testname")
        self.assertIs(obsolete_feature, feature)
        self.assertTrue(obsolete_feature.is_obsolete)

    def test_update_organism_properties(self):
        # Tests the function that transfers properties from one organism object to another
        organism1 = organism.Organism(genus="testgenus", species="testspecies", infraspecific_name="teststrain",
                                      abbreviation="testabbreviation", common_name="testname", comment="testcomment")
        organism2 = organism.Organism(genus="testgenus", species="testspecies", infraspecific_name="teststrain",
                                      abbreviation="testabbreviation", common_name="othername", comment="othercomment")
        updated = self.client.update_organism_properties(organism1, organism2)
        self.assertTrue(updated)
        self.assertEqual(organism1.common_name, "othername")

    def test_update_organismprop_properties(self):
        # Tests the function that transfers properties from one organismprop object to another
        organismprop1 = organism.OrganismProp(organism_id=1, type_id=1, value="testvalue")
        organismprop2 = organism.OrganismProp(organism_id=1, type_id=1, value="othervalue")
        updated = self.client.update_organismprop_properties(organismprop1, organismprop2)
        self.assertTrue(updated)
        self.assertEqual(organismprop1.value, "othervalue")

    def test_update_feature_properties(self):
        # Tests the function that transfers properties from one feature object to another
        feature1 = sequence.Feature(organism_id=1, type_id=1, dbxref_id=1, uniquename="testname", name="name1",
                                    residues="ACGT", seqlen=4, is_analysis=False, is_obsolete=False)
        feature2 = sequence.Feature(organism_id=1, type_id=1, dbxref_id=2, uniquename="othername", name="name2",
                                    residues="TTT", seqlen=3, is_analysis=True, is_obsolete=True)
        updated = self.client.update_feature_properties(feature1, feature2)
        self.assertTrue(updated)
        self.assertEqual(feature1.name, "name2")
        self.assertEqual(feature1.residues, "TTT")
        self.assertTrue(feature1.is_obsolete)

    def test_update_featureloc_properties(self):
        # Tests the function that transfers properties from one featureloc object to another
        featureloc1 = sequence.FeatureLoc(feature_id=1, srcfeature_id=1, fmin=0, fmax=100, strand=1, phase=1)
        featureloc2 = sequence.FeatureLoc(feature_id=1, srcfeature_id=1, fmin=20, fmax=30, strand=-1, phase=2)
        updated = self.client.update_featureloc_properties(featureloc1, featureloc2)
        self.assertTrue(updated)
        self.assertEqual(featureloc1.fmin, 20)
        self.assertEqual(featureloc1.strand, -1)

    def test_update_synonym_properties(self):
        # Tests the function that transfers properties from one synonym object to another
        synonym1 = sequence.Synonym(name="testname", type_id=1, synonym_sgml="testsgml")
        synonym2 = sequence.Synonym(name="testname", type_id=1, synonym_sgml="othersgml")
        updated = self.client.update_synonym_properties(synonym1, synonym2)
        self.assertTrue(updated)
        self.assertEqual(synonym1.synonym_sgml, "othersgml")

    def test_update_feature_synonym_properties(self):
        # Tests the function that transfers properties from one feature_synonym object to another
        feature_synonym1 = sequence.FeatureSynonym(synonym_id=1, feature_id=1, pub_id=1, is_current=True,
                                                   is_internal=True)
        feature_synonym2 = sequence.FeatureSynonym(synonym_id=1, feature_id=1, pub_id=1, is_current=False,
                                                   is_internal=False)
        updated = self.client.update_feature_synonym_properties(feature_synonym1, feature_synonym2)
        self.assertTrue(updated)
        self.assertFalse(feature_synonym1.is_current)

    def test_update_feature_relationship_properties(self):
        # Tests the function that transfers properties from one feature_relationship object to another
        feature_relationship1 = sequence.FeatureRelationship(subject_id=1, object_id=1, type_id=1, value="testvalue")
        feature_relationship2 = sequence.FeatureRelationship(subject_id=1, object_id=1, type_id=1, value="othervalue")
        updated = self.client.update_feature_relationship_properties(feature_relationship1, feature_relationship2)
        self.assertTrue(updated)
        self.assertEqual(feature_relationship1.value, "othervalue")

    def test_update_feature_dbxref_properties(self):
        # Tests the function that transfers properties from one feature_dbxref object to another
        feature_dbxref1 = sequence.FeatureDbxRef(dbxref_id=1, feature_id=1, is_current=True)
        feature_dbxref2 = sequence.FeatureDbxRef(dbxref_id=1, feature_id=1, is_current=False)
        updated = self.client.update_feature_dbxref_properties(feature_dbxref1, feature_dbxref2)
        self.assertTrue(updated)
        self.assertFalse(feature_dbxref1.is_current)

    def test_update_feature_cvterm_properties(self):
        # Tests the function that transfers properties from one feature_cvterm object to another
        feature_cvterm1 = sequence.FeatureCvTerm(cvterm_id=1, feature_id=1, pub_id=1, is_not=True)
        feature_cvterm2 = sequence.FeatureCvTerm(cvterm_id=1, feature_id=1, pub_id=1, is_not=False)
        updated = self.client.update_feature_cvterm_properties(feature_cvterm1, feature_cvterm2)
        self.assertTrue(updated)
        self.assertFalse(feature_cvterm1.is_not)

    def test_update_pub_properties(self):
        # Tests the function that transfers properties from one pub object to another
        pub1 = pub.Pub(uniquename="testname", type_id=1, title="testtitle", volume="testvolume")
        pub2 = pub.Pub(uniquename="testname", type_id=1, title="othertitle", volume="othervolume")
        updated = self.client.update_pub_properties(pub1, pub2)
        self.assertTrue(updated)
        self.assertEqual(pub1.volume, "othervolume")

    def test_update_feature_cvtermprop_properties(self):
        # Tests the function that transfers properties from one feature_cvtermprop object to another
        feature_cvtermprop1 = sequence.FeatureCvTermProp(feature_cvterm_id=1, type_id=1, value="testvalue")
        feature_cvtermprop2 = sequence.FeatureCvTermProp(feature_cvterm_id=1, type_id=1, value="othervalue")
        updated = self.client.update_feature_cvtermprop_properties(feature_cvtermprop1, feature_cvtermprop2)
        self.assertTrue(updated)
        self.assertEqual(feature_cvtermprop1.value, "othervalue")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
