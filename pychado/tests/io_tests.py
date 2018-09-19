import unittest
import pronto
import sqlalchemy.engine
import sqlalchemy.orm
from pychado.io import io, load_cvterms
from pychado.orm import base, general, cv


class TestIO(unittest.TestCase):
    """Tests basic functions for accessing databases via SQL"""

    def setUp(self):
        # Establishes a database connection and creates tables
        global session, engine
        engine = sqlalchemy.create_engine("sqlite:///:memory:")
        session_maker = sqlalchemy.orm.sessionmaker(bind=engine)
        session = session_maker()
        base.Base.metadata.create_all(engine)

    def tearDown(self):
        # Closes the database connection
        session.close()
        engine.dispose()

    def test_find_or_create(self):
        # Tests the functionality for checking if entries exist in the database, and for creating new entries
        res = io.find_or_create(session, general.Db, name="testdb")
        self.assertTrue(isinstance(res, general.Db))
        self.assertEqual(res.name, "testdb")

        query = io.find(session, general.Db, name="testdb")
        res = query.first()
        self.assertTrue(isinstance(res, general.Db))
        self.assertEqual(res.name, "testdb")

        query = io.find(session, general.Db, name="anotherdb")
        res = query.first()
        self.assertIsNone(res)
        session.rollback()


class TestLoadCvterms(unittest.TestCase):
    """Tests various functions used to load CV terms from a file into a database"""

    def setUp(self):
        # Establishes a database connection and creates tables
        global session, engine
        engine = sqlalchemy.create_engine("sqlite:///:memory:")
        session_maker = sqlalchemy.orm.sessionmaker(bind=engine)
        session = session_maker()
        base.Base.metadata.create_all(engine)

    def tearDown(self):
        # Closes the database connection
        session.close()
        engine.dispose()

    @staticmethod
    def insert_dependencies():
        # Inserts all the CV terms needed as basis for relationships and synonyms into the database
        db = io.find_or_create(session, general.Db, name="general")
        synonymtype_cv = io.find_or_create(session, cv.Cv, name="synonym_type")
        required_terms = ["exact", "narrow", "broad", "related"]
        for term in required_terms:
            dbxref = io.find_or_create(session, general.DbxRef, db_id=db.db_id, accession=term)
            io.find_or_create(session, cv.CvTerm, cv_id=synonymtype_cv.cv_id, dbxref_id=dbxref.dbxref_id, name=term)
        relationship_cv = io.find_or_create(session, cv.Cv, name="relationship")
        required_terms = ["is_a", "part_of"]
        for term in required_terms:
            dbxref = io.find_or_create(session, general.DbxRef, db_id=db.db_id, accession=term)
            io.find_or_create(session, cv.CvTerm, cv_id=relationship_cv.cv_id, dbxref_id=dbxref.dbxref_id, name=term,
                              is_relationshiptype=1)
        propertytype_cv = io.find_or_create(session, cv.Cv, name="cvterm_property_type")
        dbxref = io.find_or_create(session, general.DbxRef, db_id=db.db_id, accession="comment")
        io.find_or_create(session, cv.CvTerm, cv_id=propertytype_cv.cv_id, dbxref_id=dbxref.dbxref_id, name="comment")

    @staticmethod
    def insert_essentials():
        # Inserts CV terms needed as basis for virtually all tests
        default_db = io.find_or_create(session, general.Db, name="defaultdb")
        default_dbxref = io.find_or_create(session, general.DbxRef, db_id=default_db.db_id,
                                           accession="defaultaccession")
        default_cv = io.find_or_create(session, cv.Cv, name="defaultcv")
        default_cvterm = io.find_or_create(session, cv.CvTerm, cv_id=default_cv.cv_id,
                                           dbxref_id=default_dbxref.dbxref_id, name="testterm")
        return default_db, default_dbxref, default_cv, default_cvterm

    def test_split_dbxref(self):
        # Checks the splitting of a given database cross reference into its constituents
        result = load_cvterms.split_dbxref("testdb:testaccession:testversion")
        self.assertEqual(result[0], "testdb")
        self.assertEqual(result[1], "testaccession")
        self.assertEqual(result[2], "testversion")

        result = load_cvterms.split_dbxref("testdb:testaccession")
        self.assertEqual(result[0], "testdb")
        self.assertEqual(result[1], "testaccession")
        self.assertEqual(result[2], "")

        with self.assertRaises(AttributeError):
            load_cvterms.split_dbxref("testdb_testaccession")

    def test_create_dbxref(self):
        # Checks the creation of a database cross reference from its constituents
        result = load_cvterms.create_dbxref("testdb", "testaccession", "testversion")
        self.assertEqual(result, "testdb:testaccession:testversion")

        result = load_cvterms.create_dbxref("testdb", "testaccession")
        self.assertEqual(result, "testdb:testaccession")

        with self.assertRaises(AttributeError):
            load_cvterms.create_dbxref("testdb", "")

    def test_create_cvterm_entry(self):
        # Checks if an ontology term is correctly converted into a CV term entry
        term = pronto.Term(id="testid", name="testname", desc="testdescription", other={"is_obsolete": ["True"]})
        cvterm_entry = load_cvterms.create_cvterm_entry(term, 100, 200)
        self.assertEqual(cvterm_entry, cv.CvTerm(cv_id=100, dbxref_id=200, name="testname",
                                                 definition="testdescription", is_obsolete=1))
        term = pronto.Term(id="otherid", name="othername", other={"is_obsolete": ["False"]})
        cvterm_entry = load_cvterms.create_cvterm_entry(term, 10, 20)
        self.assertEqual(cvterm_entry, cv.CvTerm(cv_id=10, dbxref_id=20, name="othername", is_obsolete=0))

    def test_update_cvterm_properties(self):
        # Checks if the properties of a CV term are correctly updated
        input_term = cv.CvTerm(cv_id=100, dbxref_id=200, name="testname", definition="testdescription", is_obsolete=1)
        output_term = cv.CvTerm(cv_id=1, dbxref_id=200, name="newname")
        self.assertNotEqual(input_term, output_term)
        self.assertTrue(load_cvterms.update_cvterm_properties(output_term, input_term))
        self.assertEqual(input_term, output_term)
        self.assertFalse(load_cvterms.update_cvterm_properties(output_term, input_term))

    def test_get_default_namespace(self):
        # Checks if the default namespace is correctly extracted from an ontology
        ontology = pronto.Ontology()
        namespace = load_cvterms.get_default_namespace(ontology)
        self.assertEqual(namespace, "")
        ontology.meta["default-namespace"] = ["mynamespace"]
        namespace = load_cvterms.get_default_namespace(ontology)
        self.assertEqual(namespace, "mynamespace")

    def test_filter_ontology(self):
        # Checks the filtering of ontology terms by a database authority
        ontology = pronto.Ontology()
        ontology.include(pronto.Term("test:001"))
        ontology.include(pronto.Term("test:002"))
        ontology.include(pronto.Term("other:001"))
        filtered_ontology = load_cvterms.filter_ontology_by_db(ontology, "test")
        self.assertEqual(len(filtered_ontology), 2)
        self.assertIn("001", filtered_ontology)
        self.assertEqual(filtered_ontology["001"].id, "test:001")

    def test_load_and_check_dependencies(self):
        # Tests the loading of various entries from the database
        with self.assertRaises(load_cvterms.DatabaseError):
            load_cvterms.load_and_check_dependencies(session)
        self.insert_dependencies()
        (comment_term, synonym_type_terms, relationship_terms) = load_cvterms.load_and_check_dependencies(session)
        self.assertEqual(comment_term.name, "comment")
        self.assertIn("exact", synonym_type_terms)
        self.assertIn("is_a", relationship_terms)
        session.rollback()

    def test_handle_cv(self):
        # Tests the insertion of CV entries

        # Insert a new entry
        term = pronto.Term("testdb:testaccession")
        first_cv = load_cvterms.handle_cv(session, term, "testnamespace")
        self.assertEqual(first_cv.name, "testnamespace")
        self.assertIsNotNone(first_cv.cv_id)

        # Try to insert an entry without namespace, and fail
        with self.assertRaises(load_cvterms.InputFileError):
            load_cvterms.handle_cv(session, term, "")

        # Insert a further entry with another namespace
        term.other = {"namespace": ["othernamespace"]}
        second_cv = load_cvterms.handle_cv(session, term, "")
        self.assertEqual(second_cv.name, "othernamespace")
        self.assertNotEqual(first_cv.cv_id, second_cv.cv_id)

        # Try to insert an entry with the same namespace, and check that the function returns the existing entry
        third_cv = load_cvterms.handle_cv(session, term, "")
        self.assertEqual(third_cv.cv_id, second_cv.cv_id)
        session.rollback()

    def test_handle_dbxref(self):
        # Tests the insertion and update of dbxref entries

        # Populate the database with essentials
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()

        # Insert a new entry
        term = pronto.Term("defaultdb:testaccession")
        first_dbxref = load_cvterms.handle_dbxref(session, term, default_db)
        self.assertEqual(first_dbxref.accession, "testaccession")
        self.assertEqual(first_dbxref.version, "")
        self.assertIsNotNone(first_dbxref.dbxref_id)

        # Insert a further entry with another accession
        term.id = "defaultdb:otheraccession"
        second_dbxref = load_cvterms.handle_dbxref(session, term, default_db)
        self.assertEqual(second_dbxref.accession, "otheraccession")
        self.assertNotEqual(first_dbxref.dbxref_id, second_dbxref.dbxref_id)

        # Try to insert an entry with the same accession, but other version, and check that the function returns
        # the existing entry with updated version
        term.id = "defaultdb:testaccession:testversion"
        third_dbxref = load_cvterms.handle_dbxref(session, term, default_db)
        self.assertEqual(third_dbxref.accession, "testaccession")
        self.assertEqual(third_dbxref.version, "testversion")
        self.assertEqual(first_dbxref.dbxref_id, third_dbxref.dbxref_id)
        session.rollback()

    def test_is_cvterm_unique(self):
        # Tests the functionality that checks if a CV term is unique in a database

        # Populate the database with essentials, including one CV term entry as base for comparisons
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()

        # Test a CV term with same dbxref and same properties - should be unique
        (is_unique, term, dbxref) = load_cvterms.is_cvterm_unique(
            session, cv.CvTerm(cv_id=default_cv.cv_id, dbxref_id=default_dbxref.dbxref_id, name="testterm",
                               is_obsolete=0))
        self.assertTrue(is_unique)
        self.assertIsNotNone(term)

        # Test a CV term with same properties, but different dbxref - should not be unique
        (is_unique, term, dbxref) = load_cvterms.is_cvterm_unique(
            session, cv.CvTerm(cv_id=default_cv.cv_id, dbxref_id=default_dbxref.dbxref_id+1, name="testterm",
                               is_obsolete=0))
        self.assertFalse(is_unique)

        # Test a CV term with different properties - should be unique
        (is_unique, term, dbxref) = load_cvterms.is_cvterm_unique(
            session, cv.CvTerm(cv_id=default_cv.cv_id, dbxref_id=default_dbxref.dbxref_id+1, name="otherterm",
                               is_obsolete=1))
        self.assertTrue(is_unique)
        session.rollback()

    def test_mark_cvterm_as_obsolete(self):
        # Tests the functionality that marks a CV term as obsolete

        # Populate the database with essentials, including a CV term entry
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()

        # Mark a previously non-obsolete CV term as obsolete
        marked = load_cvterms.mark_cvterm_as_obsolete(session, default_cvterm)
        self.assertTrue(marked)
        self.assertEqual(default_cvterm.is_obsolete, 1)
        self.assertEqual(default_cvterm.name, "obsolete testterm")

        # Try to marks an already obsolete CV term as obsolete
        marked = load_cvterms.mark_cvterm_as_obsolete(session, default_cvterm)
        self.assertFalse(marked)
        self.assertEqual(default_cvterm.is_obsolete, 1)
        self.assertEqual(default_cvterm.name, "obsolete testterm")

        # Enforce marking the CV term as "even more obsolete"
        default_cvterm.name = "testterm (made obsolete)"
        marked = load_cvterms.mark_cvterm_as_obsolete(session, default_cvterm, True)
        self.assertTrue(marked)
        self.assertEqual(default_cvterm.is_obsolete, 2)
        self.assertEqual(default_cvterm.name, "testterm (made obsolete)")
        session.rollback()

    def test_handle_cvterm(self):
        # Tests the insertion and update of cvterm entries

        # Populate the database with essentials
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()
        ontology = pronto.Ontology()
        ontology.include(pronto.Term("defaultdb:001", "term1"))
        ontology.include(pronto.Term("defaultdb:002", "term2"))
        ontology_terms = load_cvterms.filter_ontology_by_db(ontology, default_db.name)

        # Call the function with a dbxref that is not part of the ontology, and check that the corresponding CV term
        # is marked as obsolete
        first_cvterm = load_cvterms.handle_cvterms_without_conflicts(session, ontology_terms, default_cv.cv_id,
                                                                     default_dbxref)
        self.assertEqual(first_cvterm.is_obsolete, 1)

        # Call the function with a dbxref that is part of the ontology and check that a CV term is created
        new_dbxref = io.find_or_create(session, general.DbxRef, db_id=default_db.db_id, accession="001")
        second_cvterm = load_cvterms.handle_cvterms_without_conflicts(session, ontology_terms, default_cv.cv_id,
                                                                      new_dbxref)
        self.assertIsNotNone(second_cvterm.cvterm_id)
        self.assertEqual(second_cvterm.dbxref_id, new_dbxref.dbxref_id)
        self.assertEqual(second_cvterm.name, "term1")

        # Call the function with changed ontology term and check that this updates the existing entry
        ontology_terms["001"].name = "newname"
        third_cvterm = load_cvterms.handle_cvterms_without_conflicts(session, ontology_terms, default_cv.cv_id,
                                                                     new_dbxref)
        self.assertEqual(second_cvterm.cvterm_id, third_cvterm.cvterm_id)
        self.assertEqual(second_cvterm.name, "newname")

        # Call the function with a dbxref that corresponds to an existing CV term
        ontology_terms["defaultaccession"] = pronto.Term("defaultdb:defaultaccession", "testterm")
        fourth_cvterm = load_cvterms.handle_cvterms_without_conflicts(session, ontology_terms, default_cv.cv_id,
                                                                      default_dbxref)
        self.assertEqual(fourth_cvterm, default_cvterm)
        session.rollback()

    def test_handle_comments(self):
        # Tests the insertion, update and deletion of comments (cvtermprop entries)

        # Populate the database with essentials
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()
        self.insert_dependencies()
        comment_cvterm = load_cvterms.load_and_check_dependencies(session)[0]

        # Check that an ontology term without comment will not create a cvtermprop entry
        term = pronto.Term("defaultdb:defaultaccession")
        first_cvtermprop = load_cvterms.handle_comments(session, term, default_cvterm, comment_cvterm.cvterm_id)
        self.assertIsNone(first_cvtermprop)

        # Insert a comment
        term.other = {"comment": ["testcomment"]}
        second_cvtermprop = load_cvterms.handle_comments(session, term, default_cvterm, comment_cvterm.cvterm_id)
        self.assertIsNotNone(second_cvtermprop.cvtermprop_id)
        self.assertEqual(second_cvtermprop.cvterm_id, default_cvterm.cvterm_id)
        self.assertEqual(second_cvtermprop.type_id, comment_cvterm.cvterm_id)
        self.assertEqual(second_cvtermprop.value, "testcomment")

        # Try to insert another comment and check that this updates the existing entry
        term.other = {"comment": ["othercomment"]}
        third_cvtermprop = load_cvterms.handle_comments(session, term, default_cvterm, comment_cvterm.cvterm_id)
        self.assertEqual(third_cvtermprop.cvtermprop_id, second_cvtermprop.cvtermprop_id)
        self.assertEqual(third_cvtermprop.value, "othercomment")
        session.rollback()

    def test_handle_synonyms(self):
        # Tests the insertion, update and deletion of synonyms of CV terms

        # Populate the database with essentials
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()
        self.insert_dependencies()
        synonymtype_terms = load_cvterms.load_and_check_dependencies(session)[1]

        # Check that an ontology term without synonym will not create a cvtermsynonym entry
        term = pronto.Term("defaultdb:defaultaccession")
        first_synonyms = load_cvterms.handle_synonyms(session, term, default_cvterm, synonymtype_terms)
        self.assertEqual(len(first_synonyms), 0)

        # Insert a synonym
        term.synonyms = {pronto.Synonym("another_name", "EXACT")}
        second_synonyms = load_cvterms.handle_synonyms(session, term, default_cvterm, synonymtype_terms)
        self.assertEqual(len(second_synonyms), 1)
        self.assertIsNotNone(second_synonyms[0].cvtermsynonym_id)
        self.assertEqual(second_synonyms[0].synonym, "another_name")
        self.assertEqual(second_synonyms[0].type_id, synonymtype_terms["exact"].cvterm_id)

        # Try to insert an existing synonym with changed scope, and check that this updates the existing entry
        term.synonyms = {pronto.Synonym("another_name", "NARROW")}
        third_synonyms = load_cvterms.handle_synonyms(session, term, default_cvterm, synonymtype_terms)
        self.assertEqual(len(third_synonyms), 1)
        self.assertEqual(third_synonyms[0].cvtermsynonym_id, second_synonyms[0].cvtermsynonym_id)
        self.assertEqual(third_synonyms[0].type_id, synonymtype_terms["narrow"].cvterm_id)

        # Insert another synonym
        term.synonyms.add(pronto.Synonym("yet_another_name", "BROAD"))
        fourth_synonyms = load_cvterms.handle_synonyms(session, term, default_cvterm, synonymtype_terms)
        self.assertEqual(len(fourth_synonyms), 2)
        session.rollback()

    def test_handle_cross_references(self):
        # Tests the insertion, update and deletion of cross references for CV terms

        # Populate the database with essentials
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()

        # Check that an ontology term without cross references will create a cvterm_dbxref entry "for definition"
        term = pronto.Term("defaultdb:defaultaccession")
        first_crossrefs = load_cvterms.handle_cross_references(session, term, default_cvterm, default_dbxref,
                                                               default_db)
        self.assertEqual(len(first_crossrefs), 1)
        self.assertIsNotNone(first_crossrefs[0].cvterm_dbxref_id)
        self.assertEqual(first_crossrefs[0].is_for_definition, 1)
        self.assertEqual(first_crossrefs[0].dbxref_id, default_dbxref.dbxref_id)

        # Insert a further cross reference
        term.other = {"alt_id": ["defaultdb:furtheraccession", "otherdb:otheraccession"]}
        second_crossrefs = load_cvterms.handle_cross_references(session, term, default_cvterm, default_dbxref,
                                                                default_db)
        self.assertEqual(len(second_crossrefs), 2)
        self.assertEqual(second_crossrefs[1].is_for_definition, 0)
        corresponding_dbxref = io.find_or_create(session, general.DbxRef, db_id=default_db.db_id,
                                                 accession="furtheraccession")
        self.assertEqual(corresponding_dbxref.dbxref_id, second_crossrefs[1].dbxref_id)
        session.rollback()

    def test_handle_relationships(self):
        # Tests the insertion, update and deletion of relationships between CV terms

        # Populate the database with essentials
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()
        other_dbxref = io.find_or_create(session, general.DbxRef, db_id=default_db.db_id,
                                         accession="otheraccession")
        other_cvterm = io.find_or_create(session, cv.CvTerm, cv_id=default_cv.cv_id,
                                         dbxref_id=other_dbxref.dbxref_id, name="otherterm")
        default_id = load_cvterms.create_dbxref(default_db.name, default_dbxref.accession)
        other_id = load_cvterms.create_dbxref(default_db.name, other_dbxref.accession)
        all_cvterms = {default_id: default_cvterm, other_id: other_cvterm}
        self.insert_dependencies()
        relationship_terms = load_cvterms.load_and_check_dependencies(session)[2]

        # Check that an ontology term without relationships will not create a cvterm_relationship entry
        term = pronto.Term("defaultdb:defaultaccession")
        first_relationships = load_cvterms.handle_relationships(session, term, default_cvterm, relationship_terms,
                                                                default_db, all_cvterms)
        self.assertEqual(len(first_relationships), 0)

        # Insert a relationship
        term.relations = {pronto.Relationship("part_of"): [pronto.Term(other_id, other_cvterm.name)]}
        second_relationships = load_cvterms.handle_relationships(session, term, default_cvterm, relationship_terms,
                                                                 default_db, all_cvterms)
        self.assertEqual(len(second_relationships), 1)
        self.assertIsNotNone(second_relationships[0].cvterm_relationship_id)
        self.assertEqual(second_relationships[0].subject_id, default_cvterm.cvterm_id)
        self.assertEqual(second_relationships[0].object_id, other_cvterm.cvterm_id)
        self.assertEqual(second_relationships[0].type_id, relationship_terms["part_of"].cvterm_id)

        # Insert a new relationship between the same terms
        term.relations.clear()
        term.relations = {pronto.Relationship("is_a"): [pronto.Term(other_id, other_cvterm.name)]}
        third_relationships = load_cvterms.handle_relationships(session, term, default_cvterm, relationship_terms,
                                                                default_db, all_cvterms)
        self.assertEqual(len(third_relationships), 1)
        self.assertEqual(third_relationships[0].type_id, relationship_terms["is_a"].cvterm_id)
        session.rollback()

    def test_mark_obsolete_terms(self):
        # Populate the database with essentials
        (default_db, default_dbxref, default_cv, default_cvterm) = self.insert_essentials()
        other_dbxref = io.find_or_create(session, general.DbxRef, db_id=default_db.db_id,
                                         accession="otheraccession")
        other_cvterm = io.find_or_create(session, cv.CvTerm, cv_id=default_cv.cv_id,
                                         dbxref_id=other_dbxref.dbxref_id, name="otherterm")

        # Check that the two inserted CV terms are marked as obsolete
        terms = {}
        marked_cvterms = load_cvterms.mark_obsolete_terms(session, terms, default_db)
        self.assertEqual(len(marked_cvterms), 2)
        self.assertIn(marked_cvterms[0].cvterm_id, [default_cvterm.cvterm_id, other_cvterm.cvterm_id])
        self.assertIn(marked_cvterms[1].cvterm_id, [default_cvterm.cvterm_id, other_cvterm.cvterm_id])
        session.rollback()


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
