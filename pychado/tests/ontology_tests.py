import os
import unittest
import pronto
from pychado.io import io, load_ontology
from pychado.orm import base, general, cv

modules_dir = os.path.dirname(os.path.abspath(load_ontology.__file__))
data_dir = os.path.join(modules_dir, '..', 'tests', 'data')


class TestLoadCvterms(unittest.TestCase):
    """Tests various functions used to load CV terms from a file into a database"""

    def setUp(self):
        # Establishes a database connection and creates tables
        global loader
        loader = load_ontology.OntologyLoader("sqlite:///:memory:")
        base.Base.metadata.create_all(loader.engine)

    @staticmethod
    def insert_dependencies():
        # Inserts all the CV terms needed as basis for relationships and synonyms into the database
        db = loader.insert_into_table(general.Db, name="general")
        synonymtype_cv = loader.insert_into_table(cv.Cv, name="synonym_type")
        required_terms = ["exact", "narrow", "broad", "related"]
        for term in required_terms:
            dbxref = loader.insert_into_table(general.DbxRef, db_id=db.db_id, accession=term)
            loader.insert_into_table(cv.CvTerm, cv_id=synonymtype_cv.cv_id, dbxref_id=dbxref.dbxref_id, name=term)
        relationship_cv = loader.insert_into_table(cv.Cv, name="relationship")
        required_terms = ["is_a", "part_of"]
        for term in required_terms:
            dbxref = loader.insert_into_table(general.DbxRef, db_id=db.db_id, accession=term)
            loader.insert_into_table(cv.CvTerm, cv_id=relationship_cv.cv_id, dbxref_id=dbxref.dbxref_id, name=term,
                                     is_relationshiptype=1)
        propertytype_cv = loader.insert_into_table(cv.Cv, name="cvterm_property_type")
        dbxref = loader.insert_into_table(general.DbxRef, db_id=db.db_id, accession="comment")
        loader.insert_into_table(cv.CvTerm, cv_id=propertytype_cv.cv_id, dbxref_id=dbxref.dbxref_id, name="comment")

    @staticmethod
    def insert_essentials():
        # Inserts CV terms needed as basis for virtually all tests
        default_db = loader.insert_into_table(general.Db, name="defaultdb")
        default_dbxref = loader.insert_into_table(general.DbxRef, db_id=default_db.db_id, accession="defaultaccession")
        default_cv = loader.insert_into_table(cv.Cv, name="defaultcv")
        default_cvterm = loader.insert_into_table(cv.CvTerm, cv_id=default_cv.cv_id,
                                                  dbxref_id=default_dbxref.dbxref_id, name="testterm")
        return default_db, default_dbxref, default_cv, default_cvterm

    def test_split_dbxref(self):
        # Checks the splitting of a given database cross reference into its constituents
        result = load_ontology.split_dbxref("testdb:testaccession:testversion")
        self.assertEqual(result[0], "testdb")
        self.assertEqual(result[1], "testaccession")
        self.assertEqual(result[2], "testversion")

        result = load_ontology.split_dbxref("testdb:testaccession")
        self.assertEqual(result[0], "testdb")
        self.assertEqual(result[1], "testaccession")
        self.assertEqual(result[2], "")

        with self.assertRaises(AttributeError):
            load_ontology.split_dbxref("testdb_testaccession")

    def test_create_dbxref(self):
        # Checks the creation of a database cross reference from its constituents
        result = load_ontology.create_dbxref("testdb", "testaccession", "testversion")
        self.assertEqual(result, "testdb:testaccession:testversion")

        result = load_ontology.create_dbxref("testdb", "testaccession")
        self.assertEqual(result, "testdb:testaccession")

        with self.assertRaises(AttributeError):
            load_ontology.create_dbxref("testdb", "")

    def test_create_cvterm_entry(self):
        # Checks if an ontology term is correctly converted into a CV term entry
        term = pronto.Term(id="testid", name="testname", desc="testdescription", other={"is_obsolete": ["True"]})
        cvterm_entry = load_ontology.create_cvterm_entry(term, 100, 200)
        self.assertEqual(cvterm_entry, cv.CvTerm(cv_id=100, dbxref_id=200, name="testname",
                                                 definition="testdescription", is_obsolete=1))
        term = pronto.Term(id="otherid", name="othername", other={"is_obsolete": ["False"]})
        cvterm_entry = load_ontology.create_cvterm_entry(term, 10, 20)
        self.assertEqual(cvterm_entry, cv.CvTerm(cv_id=10, dbxref_id=20, name="othername", is_obsolete=0))

    def test_update_cvterm_properties(self):
        # Checks if the properties of a CV term are correctly updated
        input_term = cv.CvTerm(cv_id=100, dbxref_id=200, name="testname", definition="testdescription", is_obsolete=1)
        output_term = cv.CvTerm(cv_id=1, dbxref_id=200, name="newname")
        self.assertNotEqual(input_term, output_term)
        self.assertTrue(load_ontology.update_cvterm_properties(output_term, input_term))
        self.assertEqual(input_term, output_term)
        self.assertFalse(load_ontology.update_cvterm_properties(output_term, input_term))

    def test_ontology_parser(self):
        # checks if an ontology file is parsed correctly
        filename = os.path.join(data_dir, "io_obo_example.obo")
        content = load_ontology.parse_ontology(filename)
        self.assertEqual(len(content), 2)
        self.assertIn("test:0000001", content)
        term = content["test:0000001"]
        self.assertEqual(term.name, "diplodocus")
        self.assertEqual(term.desc, "definition of a diplodocus")
        self.assertEqual(term.other["namespace"][0], "animals")
        self.assertEqual(len(term.relations), 1)

    def test_get_default_namespace(self):
        # Checks if the default namespace is correctly extracted from an ontology
        ontology = pronto.Ontology()
        namespace = load_ontology.get_default_namespace(ontology)
        self.assertEqual(namespace, "")
        ontology.meta["default-namespace"] = ["mynamespace"]
        namespace = load_ontology.get_default_namespace(ontology)
        self.assertEqual(namespace, "mynamespace")

    def test_filter_ontology(self):
        # Checks the filtering of ontology terms by a database authority
        ontology = pronto.Ontology()
        ontology.include(pronto.Term("test:001:abc"))
        ontology.include(pronto.Term("test:002"))
        ontology.include(pronto.Term("other:001"))
        filtered_ontology = load_ontology.filter_ontology_by_db(ontology, "test")
        self.assertEqual(len(filtered_ontology), 2)
        self.assertIn("test:001:abc", filtered_ontology)
        self.assertEqual(filtered_ontology["test:002"].id, "test:002")

    def test_extract_comments(self):
        # Tests the extraction of comments from an ontology term
        term = pronto.Term("testid")
        comment = load_ontology.extract_comment(term)
        self.assertEqual(comment, "")
        term.other = {"comment": ["testcomment"]}
        comment = load_ontology.extract_comment(term)
        self.assertEqual(comment, "testcomment")

    def test_extract_synonyms(self):
        # Tests the extraction of synonyms from an ontology term
        term = pronto.Term("testid")
        synonyms = load_ontology.extract_synonyms(term)
        self.assertEqual(len(synonyms), 0)
        term.synonyms = {pronto.Synonym("first_synonym"), pronto.Synonym("second_synonym")}
        synonyms = load_ontology.extract_synonyms(term)
        self.assertEqual(len(synonyms), 2)
        self.assertIn("second_synonym", synonyms)

    def test_extract_cross_references(self):
        # Tests the extraction of cross references from an ontology term
        term = pronto.Term("testid")
        crossrefs = load_ontology.extract_cross_references(term)
        self.assertEqual(len(crossrefs), 0)
        term.other = {"alt_id": ["alternative_id"], "xref": ["first_ref", "second_ref"]}
        crossrefs = load_ontology.extract_cross_references(term)
        self.assertEqual(len(crossrefs), 3)
        self.assertIn("alternative_id", crossrefs)
        self.assertIn("second_ref", crossrefs)

    def test_load_and_check_dependencies(self):
        # Tests the loading of various entries from the database
        with self.assertRaises(io.DatabaseError):
            loader._load_and_check_dependencies()
        self.insert_dependencies()
        (comment_term, synonym_type_terms, relationship_terms) = loader._load_and_check_dependencies()
        self.assertEqual(comment_term.name, "comment")
        self.assertIn("exact", synonym_type_terms)
        self.assertIn("is_a", relationship_terms)
        loader.rollback()

    def test_handle_cv(self):
        # Tests the insertion of CV entries

        # Insert a new entry
        term = pronto.Term("testdb:testaccession")
        first_cv = loader._handle_cv(term, "testnamespace")
        self.assertEqual(first_cv.name, "testnamespace")
        self.assertIsNotNone(first_cv.cv_id)

        # Try to insert an entry without namespace, and fail
        with self.assertRaises(io.InputFileError):
            loader._handle_cv(term, "")

        # Insert a further entry with another namespace
        term.other = {"namespace": ["othernamespace"]}
        second_cv = loader._handle_cv(term, "")
        self.assertEqual(second_cv.name, "othernamespace")
        self.assertNotEqual(first_cv.cv_id, second_cv.cv_id)

        # Try to insert an entry with the same namespace, and check that the function returns the existing entry
        third_cv = loader._handle_cv(term, "")
        self.assertEqual(third_cv.cv_id, second_cv.cv_id)
        loader.rollback()

    def test_handle_dbxref(self):
        # Tests the insertion and update of dbxref entries

        # Populate the database with essentials
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()

        # Insert a new entry
        term = pronto.Term("defaultdb:testaccession")
        first_dbxref = loader._handle_dbxref(term, default_db)
        self.assertEqual(first_dbxref.accession, "testaccession")
        self.assertEqual(first_dbxref.version, "")
        self.assertIsNotNone(first_dbxref.dbxref_id)

        # Insert a further entry with another accession
        term.id = "defaultdb:otheraccession"
        second_dbxref = loader._handle_dbxref(term, default_db)
        self.assertEqual(second_dbxref.accession, "otheraccession")
        self.assertNotEqual(first_dbxref.dbxref_id, second_dbxref.dbxref_id)

        # Try to insert an entry with the same accession, but other version, and check that the function returns
        # the existing entry with updated version
        term.id = "defaultdb:testaccession:testversion"
        third_dbxref = loader._handle_dbxref(term, default_db)
        self.assertEqual(third_dbxref.accession, "testaccession")
        self.assertEqual(third_dbxref.version, "testversion")
        self.assertEqual(first_dbxref.dbxref_id, third_dbxref.dbxref_id)
        loader.rollback()

    def test_is_cvterm_unique(self):
        # Tests the functionality that checks if a CV term is unique in a database

        # Populate the database with essentials, including one CV term entry as base for comparisons
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()

        # Test a CV term with same dbxref and same properties - should be unique
        (is_unique, term, dbxref) = loader._is_cvterm_unique(cv.CvTerm(
            cv_id=default_cv.cv_id, dbxref_id=default_dbxref.dbxref_id, name="testterm", is_obsolete=0))
        self.assertTrue(is_unique)
        self.assertIsNotNone(term)

        # Test a CV term with same properties, but different dbxref - should not be unique
        (is_unique, term, dbxref) = loader._is_cvterm_unique(cv.CvTerm(
            cv_id=default_cv.cv_id, dbxref_id=default_dbxref.dbxref_id+1, name="testterm", is_obsolete=0))
        self.assertFalse(is_unique)

        # Test a CV term with different properties - should be unique
        (is_unique, term, dbxref) = loader._is_cvterm_unique(
            cv.CvTerm(cv_id=default_cv.cv_id, dbxref_id=default_dbxref.dbxref_id+1, name="otherterm", is_obsolete=1))
        self.assertTrue(is_unique)
        loader.rollback()

    def test_mark_cvterm_as_obsolete(self):
        # Tests the functionality that marks a CV term as obsolete

        # Populate the database with essentials, including a CV term entry
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()

        # Mark a previously non-obsolete CV term as obsolete
        marked = loader._mark_cvterm_as_obsolete(default_cvterm)
        self.assertTrue(marked)
        self.assertEqual(default_cvterm.is_obsolete, 1)
        self.assertEqual(default_cvterm.name, "obsolete testterm")

        # Try to mark an already obsolete CV term as obsolete
        marked = loader._mark_cvterm_as_obsolete(default_cvterm)
        self.assertFalse(marked)
        self.assertEqual(default_cvterm.is_obsolete, 1)
        self.assertEqual(default_cvterm.name, "obsolete testterm")

        # Enforce marking a CV term as "even more obsolete" by testing an obsolete CV term with the same properties
        # as a term existing in the database
        further_dbxref = loader.insert_into_table(general.DbxRef, db_id=default_db.db_id, accession="furtheraccession")
        further_cvterm = cv.CvTerm(cv_id=default_cvterm.cv_id, dbxref_id=further_dbxref.dbxref_id,
                                   name=default_cvterm.name, is_obsolete=1)
        marked = loader._mark_cvterm_as_obsolete(further_cvterm)
        self.assertTrue(marked)
        self.assertEqual(further_cvterm.is_obsolete, 2)
        self.assertEqual(further_cvterm.name, "obsolete testterm")
        loader.rollback()

    def test_handle_cvterm(self):
        # Tests the insertion and update of cvterm entries

        # Populate the database with essentials
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()
        ontology_terms = {"defaultdb:001": pronto.Term("defaultdb:001", "term1"),
                          "defaultdb:002": pronto.Term("defaultdb:002", "term2")}

        # Call the function with a dbxref that is not part of the ontology, and check that the corresponding CV term
        # is marked as obsolete
        obsolete_cvterm = loader._handle_cvterms(ontology_terms, default_db, default_dbxref, default_cv.cv_id)
        self.assertEqual(obsolete_cvterm.is_obsolete, 1)
        self.assertEqual(loader._cvterm_inserts, 0)
        self.assertEqual(loader._cvterm_updates, 0)
        self.assertEqual(loader._cvterm_deletes, 1)

        # Call the function with a dbxref that is part of the ontology, and check that a CV term is created
        novel_dbxref = loader.insert_into_table(general.DbxRef, db_id=default_db.db_id, accession="001")
        novel_cvterm = loader._handle_cvterms(ontology_terms, default_db, novel_dbxref, default_cv.cv_id)
        self.assertIsNotNone(novel_cvterm.cvterm_id)
        self.assertEqual(novel_cvterm.dbxref_id, novel_dbxref.dbxref_id)
        self.assertEqual(novel_cvterm.name, "term1")
        self.assertEqual(loader._cvterm_inserts, 1)
        self.assertEqual(loader._cvterm_updates, 0)
        self.assertEqual(loader._cvterm_deletes, 1)

        # Call the function with changed ontology term, and check that this updates the existing entry
        ontology_terms["defaultdb:001"].name = "newname"
        updated_cvterm = loader._handle_cvterms(ontology_terms, default_db, novel_dbxref, default_cv.cv_id)
        self.assertEqual(novel_cvterm.cvterm_id, updated_cvterm.cvterm_id)
        self.assertEqual(updated_cvterm.name, "newname")
        self.assertEqual(loader._cvterm_inserts, 1)
        self.assertEqual(loader._cvterm_updates, 1)
        self.assertEqual(loader._cvterm_deletes, 1)

        # Call the function with a dbxref that corresponds to an existing CV term, and check that nothing happens
        unaltered_cvterm = loader._handle_cvterms(ontology_terms, default_db, novel_dbxref, default_cv.cv_id)
        self.assertEqual(unaltered_cvterm, updated_cvterm)
        self.assertEqual(loader._cvterm_inserts, 1)
        self.assertEqual(loader._cvterm_updates, 1)
        self.assertEqual(loader._cvterm_deletes, 1)

        # Call the function with an obsolete ontology term that has the same properties as an existing CV term, and
        # check that the new CV term is marked as 'more obsolete' before insertion
        ontology_terms["defaultdb:003"] = pronto.Term("defaultdb:003", "testterm", other={"is_obsolete": ["True"]})
        duplicate_obsolete_dbxref = loader.insert_into_table(general.DbxRef, db_id=default_db.db_id, accession="003")
        duplicate_obsolete_cvterm = loader._handle_cvterms(ontology_terms, default_db, duplicate_obsolete_dbxref,
                                                           default_cv.cv_id)
        self.assertEqual(obsolete_cvterm.is_obsolete, 1)
        self.assertEqual(duplicate_obsolete_cvterm.is_obsolete, 2)
        self.assertEqual(loader._cvterm_inserts, 2)
        self.assertEqual(loader._cvterm_updates, 1)
        self.assertEqual(loader._cvterm_deletes, 1)

        # Call the function with a non-obsolete ontology term that has the same properties as an existing CV term, and
        # check that the existing term is updated first
        ontology_terms["defaultdb:001"].name = "oldname"
        ontology_terms["defaultdb:004"] = pronto.Term("defaultdb:004", "newname")
        duplicate_dbxref = loader.insert_into_table(general.DbxRef, db_id=default_db.db_id, accession="004")
        duplicate_cvterm = loader._handle_cvterms(ontology_terms, default_db, duplicate_dbxref, default_cv.cv_id)
        self.assertEqual(novel_cvterm.name, "oldname")
        self.assertEqual(duplicate_cvterm.name, "newname")
        self.assertEqual(loader._cvterm_inserts, 3)
        self.assertEqual(loader._cvterm_updates, 2)
        self.assertEqual(loader._cvterm_deletes, 1)
        loader.rollback()

    def test_handle_comments(self):
        # Tests the insertion, update and deletion of comments (cvtermprop entries)

        # Populate the database with essentials
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()
        self.insert_dependencies()
        comment_cvterm = loader._load_and_check_dependencies()[0]

        # Check that an ontology term without comment will not create a cvtermprop entry
        term = pronto.Term("defaultdb:defaultaccession")
        first_cvtermprop = loader._handle_comments(term, default_cvterm, comment_cvterm.cvterm_id)
        self.assertIsNone(first_cvtermprop)

        # Insert a comment
        term.other = {"comment": ["testcomment"]}
        second_cvtermprop = loader._handle_comments(term, default_cvterm, comment_cvterm.cvterm_id)
        self.assertIsNotNone(second_cvtermprop.cvtermprop_id)
        self.assertEqual(second_cvtermprop.cvterm_id, default_cvterm.cvterm_id)
        self.assertEqual(second_cvtermprop.type_id, comment_cvterm.cvterm_id)
        self.assertEqual(second_cvtermprop.value, "testcomment")

        # Try to insert another comment and check that this updates the existing entry
        term.other = {"comment": ["othercomment"]}
        third_cvtermprop = loader._handle_comments(term, default_cvterm, comment_cvterm.cvterm_id)
        self.assertEqual(third_cvtermprop.cvtermprop_id, second_cvtermprop.cvtermprop_id)
        self.assertEqual(third_cvtermprop.value, "othercomment")
        loader.rollback()

    def test_handle_synonyms(self):
        # Tests the insertion, update and deletion of synonyms of CV terms

        # Populate the database with essentials
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()
        self.insert_dependencies()
        synonymtype_terms = loader._load_and_check_dependencies()[1]

        # Check that an ontology term without synonym will not create a cvtermsynonym entry
        term = pronto.Term("defaultdb:defaultaccession")
        first_synonyms = loader._handle_synonyms(term, default_cvterm, synonymtype_terms)
        self.assertEqual(len(first_synonyms), 0)

        # Insert a synonym
        term.synonyms = {pronto.Synonym("another_name", "EXACT")}
        second_synonyms = loader._handle_synonyms(term, default_cvterm, synonymtype_terms)
        self.assertEqual(len(second_synonyms), 1)
        self.assertIsNotNone(second_synonyms[0].cvtermsynonym_id)
        self.assertEqual(second_synonyms[0].synonym, "another_name")
        self.assertEqual(second_synonyms[0].type_id, synonymtype_terms["exact"].cvterm_id)

        # Try to insert an existing synonym with changed scope, and check that this updates the existing entry
        term.synonyms = {pronto.Synonym("another_name", "NARROW")}
        third_synonyms = loader._handle_synonyms(term, default_cvterm, synonymtype_terms)
        self.assertEqual(len(third_synonyms), 1)
        self.assertEqual(third_synonyms[0].cvtermsynonym_id, second_synonyms[0].cvtermsynonym_id)
        self.assertEqual(third_synonyms[0].type_id, synonymtype_terms["narrow"].cvterm_id)

        # Insert another synonym
        term.synonyms.add(pronto.Synonym("yet_another_name", "BROAD"))
        fourth_synonyms = loader._handle_synonyms(term, default_cvterm, synonymtype_terms)
        self.assertEqual(len(fourth_synonyms), 2)
        loader.rollback()

    def test_handle_cross_references(self):
        # Tests the insertion, update and deletion of cross references for CV terms

        # Populate the database with essentials
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()

        # Check that an ontology term without cross references will not create a cvterm_dbxref entry
        term = pronto.Term("defaultdb:defaultaccession")
        first_crossrefs = loader._handle_cross_references(term, default_cvterm)
        self.assertEqual(len(first_crossrefs), 0)

        # Insert a further cross reference to the same database
        term.other = {"alt_id": ["defaultdb:furtheraccession"]}
        second_crossrefs = loader._handle_cross_references(term, default_cvterm)
        self.assertEqual(len(second_crossrefs), 1)
        corresponding_dbxref = loader.find_or_insert(general.DbxRef, db_id=default_db.db_id,
                                                     accession="furtheraccession")
        self.assertEqual(corresponding_dbxref.dbxref_id, second_crossrefs[0].dbxref_id)

        # Insert a cross reference to another database
        term.other = {"xref": ["otherdb:otheraccession 'with comment'"]}
        third_crossrefs = loader._handle_cross_references(term, default_cvterm)
        self.assertEqual(len(third_crossrefs), 1)
        other_db = loader.query_table(general.Db, name="otherdb").first()
        self.assertIsNotNone(other_db)
        corresponding_dbxref = loader.find_or_insert(general.DbxRef, db_id=other_db.db_id,
                                                     accession="otheraccession")
        self.assertEqual(corresponding_dbxref.dbxref_id, third_crossrefs[0].dbxref_id)
        loader.rollback()

    def test_handle_relationships(self):
        # Tests the insertion, update and deletion of relationships between CV terms

        # Populate the database with essentials
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()
        other_dbxref = loader.insert_into_table(general.DbxRef, db_id=default_db.db_id, accession="otheraccession")
        other_cvterm = loader.insert_into_table(cv.CvTerm, cv_id=default_cv.cv_id,
                                                dbxref_id=other_dbxref.dbxref_id, name="otherterm")
        default_id = load_ontology.create_dbxref(default_db.name, default_dbxref.accession)
        other_id = load_ontology.create_dbxref(default_db.name, other_dbxref.accession)
        all_cvterms = {default_id: default_cvterm, other_id: other_cvterm}
        self.insert_dependencies()
        relationship_terms = loader._load_and_check_dependencies()[2]

        # Check that an ontology term without relationships will not create a cvterm_relationship entry
        term = pronto.Term("defaultdb:defaultaccession")
        first_relationships = loader._handle_relationships(term, default_cvterm, relationship_terms, all_cvterms)
        self.assertEqual(len(first_relationships), 0)

        # Insert a relationship
        term.relations = {pronto.Relationship("part_of"): [pronto.Term(other_id, other_cvterm.name)]}
        second_relationships = loader._handle_relationships(term, default_cvterm, relationship_terms, all_cvterms)
        self.assertEqual(len(second_relationships), 1)
        self.assertIsNotNone(second_relationships[0].cvterm_relationship_id)
        self.assertEqual(second_relationships[0].subject_id, default_cvterm.cvterm_id)
        self.assertEqual(second_relationships[0].object_id, other_cvterm.cvterm_id)
        self.assertEqual(second_relationships[0].type_id, relationship_terms["part_of"].cvterm_id)

        # Insert a new relationship between the same terms
        term.relations.clear()
        term.relations = {pronto.Relationship("is_a"): [pronto.Term(other_id, other_cvterm.name)]}
        third_relationships = loader._handle_relationships(term, default_cvterm, relationship_terms, all_cvterms)
        self.assertEqual(len(third_relationships), 1)
        self.assertEqual(third_relationships[0].type_id, relationship_terms["is_a"].cvterm_id)
        loader.rollback()

    def test_mark_obsolete_terms(self):
        # Populate the database with essentials
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()
        other_dbxref = loader.insert_into_table(general.DbxRef, db_id=default_db.db_id, accession="otheraccession")
        other_cvterm = loader.insert_into_table(cv.CvTerm, cv_id=default_cv.cv_id, dbxref_id=other_dbxref.dbxref_id,
                                                name="otherterm")

        # Check that the two inserted CV terms are marked as obsolete
        terms = {}
        marked_cvterms = loader._mark_obsolete_terms(terms, default_db)
        self.assertEqual(len(marked_cvterms), 2)
        self.assertIn(marked_cvterms[0].cvterm_id, [default_cvterm.cvterm_id, other_cvterm.cvterm_id])
        self.assertIn(marked_cvterms[1].cvterm_id, [default_cvterm.cvterm_id, other_cvterm.cvterm_id])
        loader.rollback()


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
