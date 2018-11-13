import os
import unittest
import pronto
from .. import dbutils, utils
from ..io import iobase, essentials, ontology
from ..orm import base, general, cv


class TestOntology(unittest.TestCase):
    """Tests various functions used to load an ontology from a file into a database"""

    modules_dir = os.path.dirname(os.path.abspath(ontology.__file__))
    data_dir = os.path.join(modules_dir, '..', 'tests', 'data')
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
        essentials_client._load_further_relationship_entries()
        cls.client = ontology.OntologyClient(cls.connection_uri)

    @classmethod
    def tearDownClass(cls):
        # Drops the database
        dbutils.drop_database(cls.connection_uri, True)

    def setUp(self):
        # Inserts default entries into database tables
        (self.default_db, self.default_dbxref, self.default_cv, self.default_cvterm) = self.insert_default_entries()

    def tearDown(self):
        # Rolls back all changes to the database
        self.client.session.rollback()

    def insert_default_entries(self):
        # Inserts CV terms needed as basis for virtually all tests
        default_db = general.Db(name="defaultdb")
        self.client.add_and_flush(default_db)
        default_dbxref = general.DbxRef(db_id=default_db.db_id, accession="defaultaccession")
        self.client.add_and_flush(default_dbxref)
        default_cv = cv.Cv(name="defaultcv")
        self.client.add_and_flush(default_cv)
        default_cvterm = cv.CvTerm(cv_id=default_cv.cv_id, dbxref_id=default_dbxref.dbxref_id, name="testterm")
        self.client.add_and_flush(default_cvterm)
        return default_db, default_dbxref, default_cv, default_cvterm

    def test_split_dbxref(self):
        # Checks the splitting of a given database cross reference into its constituents
        result = ontology.split_dbxref("testdb:testaccession:testversion")
        self.assertEqual(result[0], "testdb")
        self.assertEqual(result[1], "testaccession")
        self.assertEqual(result[2], "testversion")

        result = ontology.split_dbxref("testdb:testaccession")
        self.assertEqual(result[0], "testdb")
        self.assertEqual(result[1], "testaccession")
        self.assertEqual(result[2], "")

        with self.assertRaises(AttributeError):
            ontology.split_dbxref("testdb_testaccession")

    def test_create_dbxref(self):
        # Checks the creation of a database cross reference from its constituents
        result = ontology.create_dbxref("testdb", "testaccession", "testversion")
        self.assertEqual(result, "testdb:testaccession:testversion")

        result = ontology.create_dbxref("testdb", "testaccession")
        self.assertEqual(result, "testdb:testaccession")

        with self.assertRaises(AttributeError):
            ontology.create_dbxref("testdb", "")

    def test_create_cvterm_entry(self):
        # Checks if an ontology term is correctly converted into a CV term entry
        term = pronto.Term(id="testid", name="testname", desc="testdescription", other={"is_obsolete": ["True"]})
        cvterm_entry = ontology.create_cvterm_entry(term, 100, 200)
        self.assertEqual(cvterm_entry, cv.CvTerm(cv_id=100, dbxref_id=200, name="testname",
                                                 definition="testdescription", is_obsolete=1))
        term = pronto.Term(id="otherid", name="othername", other={"is_obsolete": ["False"]})
        cvterm_entry = ontology.create_cvterm_entry(term, 10, 20)
        self.assertEqual(cvterm_entry, cv.CvTerm(cv_id=10, dbxref_id=20, name="othername", is_obsolete=0))

    def test_update_cvterm_properties(self):
        # Checks if the properties of a CV term are correctly updated
        input_term = cv.CvTerm(cv_id=100, dbxref_id=200, name="testname", definition="testdescription", is_obsolete=1)
        output_term = cv.CvTerm(cv_id=1, dbxref_id=200, name="newname")
        self.assertNotEqual(input_term, output_term)
        self.assertTrue(ontology.update_cvterm_properties(output_term, input_term))
        self.assertEqual(input_term, output_term)
        self.assertFalse(ontology.update_cvterm_properties(output_term, input_term))

    def test_ontology_parser(self):
        # checks if an ontology file is parsed correctly
        filename = os.path.join(self.data_dir, "io_obo_example.obo")
        content = ontology.parse_ontology(filename)
        self.assertEqual(len(content), 2)
        self.assertIn("test:0000001", content)
        term = content["test:0000001"]
        self.assertEqual(term.name, "diplodocus")
        self.assertEqual(term.desc, "definition of a diplodocus")
        self.assertEqual(term.other["namespace"][0], "animals")
        self.assertEqual(len(term.relations), 1)

    def test_get_default_namespace(self):
        # Checks if the default namespace is correctly extracted from an ontology
        ont = pronto.Ontology()
        namespace = ontology.get_default_namespace(ont)
        self.assertEqual(namespace, "")
        ont.meta["default-namespace"] = ["mynamespace"]
        namespace = ontology.get_default_namespace(ont)
        self.assertEqual(namespace, "mynamespace")

    def test_filter_ontology(self):
        # Checks the filtering of ontology terms by a database authority
        ont = pronto.Ontology()
        ont.include(pronto.Term("test:001:abc"))
        ont.include(pronto.Term("test:002"))
        ont.include(pronto.Term("other:001"))
        filtered_ontology = ontology.filter_ontology_by_db(ont, "test")
        self.assertEqual(len(filtered_ontology), 2)
        self.assertIn("test:001:abc", filtered_ontology)
        self.assertEqual(filtered_ontology["test:002"].id, "test:002")

    def test_extract_comments(self):
        # Tests the extraction of comments from an ontology term
        term = pronto.Term("testid")
        comment = ontology.extract_comment(term)
        self.assertEqual(comment, "")
        term.other = {"comment": ["testcomment"]}
        comment = ontology.extract_comment(term)
        self.assertEqual(comment, "testcomment")

    def test_extract_synonyms(self):
        # Tests the extraction of synonyms from an ontology term
        term = pronto.Term("testid")
        synonyms = ontology.extract_synonyms(term)
        self.assertEqual(len(synonyms), 0)
        term.synonyms = {pronto.Synonym("first_synonym"), pronto.Synonym("second_synonym")}
        synonyms = ontology.extract_synonyms(term)
        self.assertEqual(len(synonyms), 2)
        self.assertIn("second_synonym", synonyms)

    def test_extract_cross_references(self):
        # Tests the extraction of cross references from an ontology term
        term = pronto.Term("testid")
        crossrefs = ontology.extract_cross_references(term)
        self.assertEqual(len(crossrefs), 0)
        term.other = {"alt_id": ["alternative_id"], "xref": ["first_ref", "second_ref"]}
        crossrefs = ontology.extract_cross_references(term)
        self.assertEqual(len(crossrefs), 3)
        self.assertIn("alternative_id", crossrefs)
        self.assertIn("second_ref", crossrefs)

    def test_load_comment_term(self):
        # Tests the loading of the "comment" term from the database
        comment_term = self.client._load_comment_term()
        self.assertEqual(comment_term.name, "comment")

    def test_load_relationship_terms(self):
        # Tests the loading of relationship terms from the database
        relationship_terms = self.client._load_relationship_terms()
        self.assertIn("is_a", relationship_terms)
        self.assertEqual(relationship_terms["is_a"].is_relationshiptype, 1)

    def test_load_synonym_type_terms(self):
        # Tests the loading of synonym type terms from the database
        synonym_type_terms = self.client._load_synonym_type_terms()
        self.assertIn("exact", synonym_type_terms)

    def test_handle_db(self):
        # Tests the insertion of DB entries

        # Insert a new entry
        first_db = self.client._handle_db("testdb")
        self.assertEqual(first_db.name, "testdb")
        self.assertIsNotNone(first_db.db_id)

        # Insert a further entry with a different authority
        second_db = self.client._handle_db("anotherdb")
        self.assertNotEqual(first_db.db_id, second_db.db_id)

        # Try to insert a further entry with the same authority, and check that the function returns the existing entry
        third_db = self.client._handle_db("testdb")
        self.assertEqual(third_db.db_id, first_db.db_id)

    def test_handle_cv(self):
        # Tests the insertion of CV entries

        # Insert a new entry
        term = pronto.Term("testdb:testaccession")
        first_cv = self.client._handle_cv(term, "testnamespace")
        self.assertEqual(first_cv.name, "testnamespace")
        self.assertIsNotNone(first_cv.cv_id)

        # Try to insert an entry without namespace, and fail
        with self.assertRaises(iobase.InputFileError):
            self.client._handle_cv(term, "")

        # Insert a further entry with another namespace
        term.other = {"namespace": ["othernamespace"]}
        second_cv = self.client._handle_cv(term, "")
        self.assertEqual(second_cv.name, "othernamespace")
        self.assertNotEqual(first_cv.cv_id, second_cv.cv_id)

        # Try to insert an entry with the same namespace, and check that the function returns the existing entry
        third_cv = self.client._handle_cv(term, "")
        self.assertEqual(third_cv.cv_id, second_cv.cv_id)

    def test_handle_dbxref(self):
        # Tests the insertion and update of dbxref entries

        # Insert a new entry
        term = pronto.Term("defaultdb:testaccession")
        first_dbxref = self.client._handle_dbxref(term, self.default_db)
        self.assertEqual(first_dbxref.accession, "testaccession")
        self.assertEqual(first_dbxref.version, "")
        self.assertIsNotNone(first_dbxref.dbxref_id)

        # Insert a further entry with another accession
        term.id = "defaultdb:otheraccession"
        second_dbxref = self.client._handle_dbxref(term, self.default_db)
        self.assertEqual(second_dbxref.accession, "otheraccession")
        self.assertNotEqual(first_dbxref.dbxref_id, second_dbxref.dbxref_id)

        # Try to insert an entry with the same accession, but other version, and check that the function returns
        # the existing entry with updated version
        term.id = "defaultdb:testaccession:testversion"
        third_dbxref = self.client._handle_dbxref(term, self.default_db)
        self.assertEqual(third_dbxref.accession, "testaccession")
        self.assertEqual(third_dbxref.version, "testversion")
        self.assertEqual(first_dbxref.dbxref_id, third_dbxref.dbxref_id)

    def test_is_cvterm_unique(self):
        # Tests the functionality that checks if a CV term is unique in a database

        # Test a CV term with same dbxref and same properties - should be unique
        (is_unique, term, dbxref) = self.client._is_cvterm_unique(cv.CvTerm(
            cv_id=self.default_cv.cv_id, dbxref_id=self.default_dbxref.dbxref_id, name="testterm", is_obsolete=0))
        self.assertTrue(is_unique)
        self.assertIsNotNone(term)

        # Test a CV term with same properties, but different dbxref - should not be unique
        (is_unique, term, dbxref) = self.client._is_cvterm_unique(cv.CvTerm(
            cv_id=self.default_cv.cv_id, dbxref_id=self.default_dbxref.dbxref_id+1, name="testterm", is_obsolete=0))
        self.assertFalse(is_unique)

        # Test a CV term with different properties - should be unique
        (is_unique, term, dbxref) = self.client._is_cvterm_unique(cv.CvTerm(
            cv_id=self.default_cv.cv_id, dbxref_id=self.default_dbxref.dbxref_id+1, name="otherterm", is_obsolete=1))
        self.assertTrue(is_unique)

    def test_mark_cvterm_as_obsolete(self):
        # Tests the functionality that marks a CV term as obsolete

        # Mark a previously non-obsolete CV term as obsolete
        marked = self.client._mark_cvterm_as_obsolete(self.default_cvterm)
        self.assertTrue(marked)
        self.assertEqual(self.default_cvterm.is_obsolete, 1)
        self.assertEqual(self.default_cvterm.name, "obsolete testterm")

        # Try to mark an already obsolete CV term as obsolete
        marked = self.client._mark_cvterm_as_obsolete(self.default_cvterm)
        self.assertFalse(marked)
        self.assertEqual(self.default_cvterm.is_obsolete, 1)
        self.assertEqual(self.default_cvterm.name, "obsolete testterm")

        # Enforce marking a CV term as "even more obsolete" by testing an obsolete CV term with the same properties
        # as a term existing in the database
        further_dbxref = general.DbxRef(db_id=self.default_db.db_id, accession="furtheraccession")
        self.client.add_and_flush(further_dbxref)
        further_cvterm = cv.CvTerm(cv_id=self.default_cvterm.cv_id, dbxref_id=further_dbxref.dbxref_id,
                                   name=self.default_cvterm.name, is_obsolete=1)
        marked = self.client._mark_cvterm_as_obsolete(further_cvterm)
        self.assertTrue(marked)
        self.assertEqual(further_cvterm.is_obsolete, 2)
        self.assertEqual(further_cvterm.name, "obsolete testterm")

    def test_handle_cvterm(self):
        # Tests the insertion and update of cvterm entries

        # Populate the database with essentials
        ontology_terms = {"defaultdb:001": pronto.Term("defaultdb:001", "term1"),
                          "defaultdb:002": pronto.Term("defaultdb:002", "term2")}

        # Call the function with a dbxref that is not part of the ontology, and check that the corresponding CV term
        # is marked as obsolete
        obsolete_cvterm = self.client._handle_cvterms(ontology_terms, self.default_db, self.default_dbxref,
                                                      self.default_cv.cv_id)
        self.assertEqual(obsolete_cvterm.is_obsolete, 1)
        self.assertEqual(self.client._cvterm_inserts, 0)
        self.assertEqual(self.client._cvterm_updates, 0)
        self.assertEqual(self.client._cvterm_deletes, 1)

        # Call the function with a dbxref that is part of the ontology, and check that a CV term is created
        novel_dbxref = general.DbxRef(db_id=self.default_db.db_id, accession="001")
        self.client.add_and_flush(novel_dbxref)
        novel_cvterm = self.client._handle_cvterms(ontology_terms, self.default_db, novel_dbxref, self.default_cv.cv_id)
        self.assertIsNotNone(novel_cvterm.cvterm_id)
        self.assertEqual(novel_cvterm.dbxref_id, novel_dbxref.dbxref_id)
        self.assertEqual(novel_cvterm.name, "term1")
        self.assertEqual(self.client._cvterm_inserts, 1)
        self.assertEqual(self.client._cvterm_updates, 0)
        self.assertEqual(self.client._cvterm_deletes, 1)

        # Call the function with changed ontology term, and check that this updates the existing entry
        ontology_terms["defaultdb:001"].name = "newname"
        updated_cvterm = self.client._handle_cvterms(ontology_terms, self.default_db, novel_dbxref,
                                                     self.default_cv.cv_id)
        self.assertEqual(novel_cvterm.cvterm_id, updated_cvterm.cvterm_id)
        self.assertEqual(updated_cvterm.name, "newname")
        self.assertEqual(self.client._cvterm_inserts, 1)
        self.assertEqual(self.client._cvterm_updates, 1)
        self.assertEqual(self.client._cvterm_deletes, 1)

        # Call the function with a dbxref that corresponds to an existing CV term, and check that nothing happens
        unaltered_cvterm = self.client._handle_cvterms(ontology_terms, self.default_db, novel_dbxref,
                                                       self.default_cv.cv_id)
        self.assertEqual(unaltered_cvterm, updated_cvterm)
        self.assertEqual(self.client._cvterm_inserts, 1)
        self.assertEqual(self.client._cvterm_updates, 1)
        self.assertEqual(self.client._cvterm_deletes, 1)

        # Call the function with an obsolete ontology term that has the same properties as an existing CV term, and
        # check that the new CV term is marked as 'more obsolete' before insertion
        ontology_terms["defaultdb:003"] = pronto.Term("defaultdb:003", "testterm", other={"is_obsolete": ["True"]})
        duplicate_obsolete_dbxref = general.DbxRef(db_id=self.default_db.db_id, accession="003")
        self.client.add_and_flush(duplicate_obsolete_dbxref)
        duplicate_obsolete_cvterm = self.client._handle_cvterms(ontology_terms, self.default_db,
                                                                duplicate_obsolete_dbxref, self.default_cv.cv_id)
        self.assertEqual(obsolete_cvterm.is_obsolete, 1)
        self.assertEqual(duplicate_obsolete_cvterm.is_obsolete, 2)
        self.assertEqual(self.client._cvterm_inserts, 2)
        self.assertEqual(self.client._cvterm_updates, 1)
        self.assertEqual(self.client._cvterm_deletes, 1)

        # Call the function with a non-obsolete ontology term that has the same properties as an existing CV term, and
        # check that the existing term is updated first
        ontology_terms["defaultdb:001"].name = "oldname"
        ontology_terms["defaultdb:004"] = pronto.Term("defaultdb:004", "newname")
        duplicate_dbxref = general.DbxRef(db_id=self.default_db.db_id, accession="004")
        self.client.add_and_flush(duplicate_dbxref)
        duplicate_cvterm = self.client._handle_cvterms(ontology_terms, self.default_db, duplicate_dbxref,
                                                       self.default_cv.cv_id)
        self.assertEqual(novel_cvterm.name, "oldname")
        self.assertEqual(duplicate_cvterm.name, "newname")
        self.assertEqual(self.client._cvterm_inserts, 3)
        self.assertEqual(self.client._cvterm_updates, 2)
        self.assertEqual(self.client._cvterm_deletes, 1)

    def test_handle_typedef(self):
        # Tests the insertion of relationship-type CV terms

        # Insert a new entry
        relationship = pronto.Relationship("new_relationship")
        first_typedef = self.client._handle_typedef(relationship, self.default_db, self.default_cv)
        self.assertEqual(first_typedef.name, "new_relationship")
        self.assertEqual(first_typedef.cv_id, self.default_cv.cv_id)
        self.assertTrue(first_typedef.is_relationshiptype)
        self.assertIsNotNone(first_typedef.cvterm_id)

        # Insert a further entry with a different name
        relationship = pronto.Relationship("another_relationship")
        second_typedef = self.client._handle_typedef(relationship, self.default_db, self.default_cv)
        self.assertNotEqual(first_typedef.cvterm_id, second_typedef.cvterm_id)

        # Try to insert a further entry with the same authority, and check that the function returns the existing entry
        third_typedef = self.client._handle_typedef(relationship, self.default_db, self.default_cv)
        self.assertEqual(third_typedef.cvterm_id, second_typedef.cvterm_id)

    def test_handle_comments(self):
        # Tests the insertion, update and deletion of comments (cvtermprop entries)

        # Check that an ontology term without comment will not create a cvtermprop entry
        term = pronto.Term("defaultdb:defaultaccession")
        first_cvtermprop = self.client._handle_comments(term, self.default_cvterm)
        self.assertIsNone(first_cvtermprop)

        # Insert a comment
        term.other = {"comment": ["testcomment"]}
        second_cvtermprop = self.client._handle_comments(term, self.default_cvterm)
        self.assertIsNotNone(second_cvtermprop.cvtermprop_id)
        self.assertEqual(second_cvtermprop.cvterm_id, self.default_cvterm.cvterm_id)
        self.assertEqual(second_cvtermprop.type_id, self.client._comment_term.cvterm_id)
        self.assertEqual(second_cvtermprop.value, "testcomment")

        # Try to insert another comment and check that this updates the existing entry
        term.other = {"comment": ["othercomment"]}
        third_cvtermprop = self.client._handle_comments(term, self.default_cvterm)
        self.assertEqual(third_cvtermprop.cvtermprop_id, second_cvtermprop.cvtermprop_id)
        self.assertEqual(third_cvtermprop.value, "othercomment")

    def test_handle_synonyms(self):
        # Tests the insertion, update and deletion of synonyms of CV terms

        # Check that an ontology term without synonym will not create a cvtermsynonym entry
        term = pronto.Term("defaultdb:defaultaccession")
        first_synonyms = self.client._handle_synonyms(term, self.default_cvterm)
        self.assertEqual(len(first_synonyms), 0)

        # Insert a synonym
        term.synonyms = {pronto.Synonym("another_name", "EXACT")}
        second_synonyms = self.client._handle_synonyms(term, self.default_cvterm)
        self.assertEqual(len(second_synonyms), 1)
        self.assertIsNotNone(second_synonyms[0].cvtermsynonym_id)
        self.assertEqual(second_synonyms[0].synonym, "another_name")
        self.assertEqual(second_synonyms[0].type_id, self.client._synonym_type_terms["exact"].cvterm_id)

        # Try to insert an existing synonym with changed scope, and check that this updates the existing entry
        term.synonyms = {pronto.Synonym("another_name", "NARROW")}
        third_synonyms = self.client._handle_synonyms(term, self.default_cvterm)
        self.assertEqual(len(third_synonyms), 1)
        self.assertEqual(third_synonyms[0].cvtermsynonym_id, second_synonyms[0].cvtermsynonym_id)
        self.assertEqual(third_synonyms[0].type_id, self.client._synonym_type_terms["narrow"].cvterm_id)

        # Insert another synonym
        term.synonyms.add(pronto.Synonym("yet_another_name", "BROAD"))
        fourth_synonyms = self.client._handle_synonyms(term, self.default_cvterm)
        self.assertEqual(len(fourth_synonyms), 2)

    def test_handle_cross_references(self):
        # Tests the insertion, update and deletion of cross references for CV terms

        # Check that an ontology term without cross references will not create a cvterm_dbxref entry
        term = pronto.Term("defaultdb:defaultaccession")
        first_crossrefs = self.client._handle_cross_references(term, self.default_cvterm)
        self.assertEqual(len(first_crossrefs), 0)

        # Insert a further cross reference to the same database
        term.other = {"alt_id": ["defaultdb:furtheraccession"]}
        second_crossrefs = self.client._handle_cross_references(term, self.default_cvterm)
        self.assertEqual(len(second_crossrefs), 1)
        corresponding_dbxref = self.client.find_or_insert(general.DbxRef, db_id=self.default_db.db_id,
                                                          accession="furtheraccession")
        self.assertEqual(corresponding_dbxref.dbxref_id, second_crossrefs[0].dbxref_id)

        # Insert a cross reference to another database
        term.other = {"xref": ["otherdb:otheraccession 'with comment'"]}
        third_crossrefs = self.client._handle_cross_references(term, self.default_cvterm)
        self.assertEqual(len(third_crossrefs), 1)
        other_db = self.client.query_table(general.Db, name="otherdb").first()
        self.assertIsNotNone(other_db)
        corresponding_dbxref = self.client.find_or_insert(general.DbxRef, db_id=other_db.db_id,
                                                          accession="otheraccession")
        self.assertEqual(corresponding_dbxref.dbxref_id, third_crossrefs[0].dbxref_id)

    def test_handle_relationships(self):
        # Tests the insertion, update and deletion of relationships between CV terms

        # Populate the database with essentials
        other_dbxref = general.DbxRef(db_id=self.default_db.db_id, accession="otheraccession")
        self.client.add_and_flush(other_dbxref)
        other_cvterm = cv.CvTerm(cv_id=self.default_cv.cv_id, dbxref_id=other_dbxref.dbxref_id, name="otherterm")
        self.client.add_and_flush(other_cvterm)
        default_id = ontology.create_dbxref(self.default_db.name, self.default_dbxref.accession)
        other_id = ontology.create_dbxref(self.default_db.name, other_dbxref.accession)
        all_cvterms = {default_id: self.default_cvterm, other_id: other_cvterm}

        # Check that an ontology term without relationships will not create a cvterm_relationship entry
        term = pronto.Term("defaultdb:defaultaccession")
        first_relationships = self.client._handle_relationships(term, self.default_cvterm, all_cvterms)
        self.assertEqual(len(first_relationships), 0)

        # Insert a relationship
        term.relations = {pronto.Relationship("part_of"): [pronto.Term(other_id, other_cvterm.name)]}
        second_relationships = self.client._handle_relationships(term, self.default_cvterm, all_cvterms)
        self.assertEqual(len(second_relationships), 1)
        self.assertIsNotNone(second_relationships[0].cvterm_relationship_id)
        self.assertEqual(second_relationships[0].subject_id, self.default_cvterm.cvterm_id)
        self.assertEqual(second_relationships[0].object_id, other_cvterm.cvterm_id)
        self.assertEqual(second_relationships[0].type_id, self.client._relationship_terms["part_of"].cvterm_id)

        # Insert a new relationship between the same terms
        term.relations.clear()
        term.relations = {pronto.Relationship("is_a"): [pronto.Term(other_id, other_cvterm.name)]}
        third_relationships = self.client._handle_relationships(term, self.default_cvterm, all_cvterms)
        self.assertEqual(len(third_relationships), 1)
        self.assertEqual(third_relationships[0].type_id, self.client._relationship_terms["is_a"].cvterm_id)

    def test_mark_obsolete_terms(self):
        # Populate the database with essentials
        other_dbxref = general.DbxRef(db_id=self.default_db.db_id, accession="otheraccession")
        self.client.add_and_flush(other_dbxref)
        other_cvterm = cv.CvTerm(cv_id=self.default_cv.cv_id, dbxref_id=other_dbxref.dbxref_id, name="otherterm")
        self.client.add_and_flush(other_cvterm)

        # Check that the two inserted CV terms are marked as obsolete
        terms = {}
        marked_cvterms = self.client._mark_obsolete_terms(terms, self.default_db)
        self.assertEqual(len(marked_cvterms), 2)
        self.assertIn(marked_cvterms[0].cvterm_id, [self.default_cvterm.cvterm_id, other_cvterm.cvterm_id])
        self.assertIn(marked_cvterms[1].cvterm_id, [self.default_cvterm.cvterm_id, other_cvterm.cvterm_id])


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
