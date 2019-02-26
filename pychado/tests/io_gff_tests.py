import os
import shutil
import tempfile
import filecmp
import unittest.mock
import sqlalchemy.orm
import gffutils
from .. import utils
from ..io import iobase, fasta, gff
from ..orm import general, cv, organism, pub, sequence

modules_dir = os.path.dirname(os.path.abspath(gff.__file__))
data_dir = os.path.abspath(os.path.join(modules_dir, '..', 'tests', 'data'))


class TestGFFImport(unittest.TestCase):
    """Tests various functions used to load a GFF file into a database"""

    @classmethod
    def setUpClass(cls):
        # Creates an instance of the base class to be tested and instantiates global attributes
        cls.client = gff.GFFImportClient("testuri", test_environment=True)
        cls.client._synonym_terms = {
            "synonym": cv.CvTerm(cv_id=3, dbxref_id=31, name="synonym", cvterm_id=31),
            "previous_systematic_id": cv.CvTerm(cv_id=3, dbxref_id=32, name="previous_systematic_id", cvterm_id=32),
            "alias": cv.CvTerm(cv_id=3, dbxref_id=33, name="alias", cvterm_id=33)
        }
        cls.client._sequence_terms = {
            "gene": cv.CvTerm(cv_id=4, dbxref_id=41, name="gene", cvterm_id=41),
            "mRNA": cv.CvTerm(cv_id=4, dbxref_id=42, name="gene", cvterm_id=42),
            "chromosome": cv.CvTerm(cv_id=4, dbxref_id=43, name="chromosome", cvterm_id=43)
        }
        cls.client._feature_property_terms = {
            "score": cv.CvTerm(cv_id=5, dbxref_id=51, name="score", cvterm_id=51),
            "source": cv.CvTerm(cv_id=5, dbxref_id=52, name="source", cvterm_id=52),
            "comment": cv.CvTerm(cv_id=5, dbxref_id=53, name="comment", cvterm_id=53)
        }
        cls.client._parent_terms = {
            "part_of": cv.CvTerm(cv_id=6, dbxref_id=62, name="part_of", cvterm_id=62, is_relationshiptype=1),
            "derives_from": cv.CvTerm(cv_id=6, dbxref_id=63, name="derives_from", cvterm_id=63, is_relationshiptype=1)
        }
        cls.client._default_pub = pub.Pub(uniquename="defaultpub", type_id=71, pub_id=33)
        cls.client._synonym_type_ids = [31, 32, 33]
        cls.client._feature_property_type_ids = [51, 52, 53]
        cls.client._parent_type_ids = [62, 63]
        cls.client._go_db = general.Db(db_id=131, name="GO")
        cls.client.full_attributes = True

    def setUp(self):
        # Creates a default GFF record
        self.default_gff_record = gffutils.Feature(
            id="testid", seqid="testseqid", source="testsource", featuretype="testtype", start=1, end=30, score="3.5",
            strand="+", frame="2", attributes={
                "Name": ["testname"], "translation": ["MCRA"], "literature": ["PMID:12334"], "Alias": ["testalias"],
                "previous_systematic_id": "testsynonym", "Parent": "testparent", "Dbxref": ["testdb:testaccession"],
                "Ontology_term": ["GO:7890"], "Note": "testnote"})

    def test_create_sqlite_db(self):
        # Tests the function that creates a SQLite database from a GFF file
        gff_file = os.path.join(data_dir, 'gff_without_fasta.gff3')
        self.assertTrue(os.path.exists(gff_file))
        gff_db = self.client._create_sqlite_db(gff_file)
        self.assertEqual(len(self.client._sqlite_databases), 1)
        gff_db_name = self.client._sqlite_databases[0]
        self.assertTrue(os.path.exists(gff_db_name))
        self.assertIn("gff-version 3", gff_db.directives)
        os.remove(gff_db_name)
        self.assertFalse(os.path.exists(gff_db_name))

    def test_has_fasta(self):
        # Tests the function that checks if a GFF file contains a FASTA section
        gff_file = os.path.join(data_dir, 'gff_without_fasta.gff3')
        self.assertFalse(self.client._has_fasta(gff_file))
        gff_file = os.path.join(data_dir, 'gff_with_fasta.gff3')
        self.assertTrue(self.client._has_fasta(gff_file))

    def test_split_off_fasta(self):
        # Tests the function copying the FASTA section from a GFF file into a separate file
        gff_file = os.path.join(data_dir, 'gff_with_fasta.gff3')
        fasta_file = tempfile.mkstemp()[1]
        self.client._split_off_fasta(gff_file, fasta_file)
        actual_fasta_file = os.path.join(data_dir, 'fasta_only.fa')
        self.assertTrue(filecmp.cmp(fasta_file, actual_fasta_file))
        os.remove(fasta_file)

    @unittest.mock.patch("pychado.io.fasta.FastaImportClient")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._split_off_fasta")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._has_fasta")
    def test_import_fasta(self, mock_includes: unittest.mock.Mock, mock_copy: unittest.mock.Mock,
                          mock_fasta: unittest.mock.Mock):
        # Tests the function that imports the FASTA sequences for a GFF file
        self.assertIs(mock_includes, self.client._has_fasta)
        self.assertIs(mock_copy, self.client._split_off_fasta)
        self.assertIs(mock_fasta, fasta.FastaImportClient)

        # FASTA in GFF and separate file
        mock_includes.return_value = True
        with self.assertRaises(iobase.InputFileError):
            self.client._import_fasta("testgff", "testfasta", "testorganism", "region")

        # FASTA in separate file only
        mock_includes.return_value = False
        mock_copy.reset_mock()
        mock_fasta.reset_mock()
        self.client._import_fasta("testgff", "testfasta", "testorganism", "region")
        mock_includes.assert_called_with("testgff")
        mock_copy.assert_not_called()
        mock_fasta.assert_called_with("testuri", False)
        self.assertIn(unittest.mock.call().load("testfasta", "testorganism", "region"), mock_fasta.mock_calls)

        # FASTA in GFF only
        mock_includes.return_value = True
        mock_copy.reset_mock()
        mock_fasta.reset_mock()
        self.client._import_fasta("testgff", "", "testorganism", "region")
        mock_includes.assert_called_with("testgff")
        mock_copy.assert_called()
        mock_fasta.assert_called()

        # No FASTA
        mock_includes.return_value = False
        mock_copy.reset_mock()
        mock_fasta.reset_mock()
        self.client._import_fasta("testgff", "", "testorganism", "region")
        mock_includes.assert_called_with("testgff")
        mock_copy.assert_not_called()
        mock_fasta.assert_not_called()

    @unittest.mock.patch("pychado.io.gff.GFFImportClient.query_table")
    def test_handle_existing_features(self, mock_query: unittest.mock.Mock):
        self.assertIs(mock_query, self.client.query_table)
        organism_entry = organism.Organism(genus="", species="", abbreviation="testorganism", organism_id=1)
        mock_query.return_value = unittest.mock.Mock(sqlalchemy.orm.Query)

        # update import - should not query
        self.client.fresh_load = False
        self.client.force_purge = False
        self.client._handle_existing_features(organism_entry)
        mock_query.assert_not_called()

        # from-scratch import on empty table - should not call delete
        self.client.fresh_load = True
        self.client.force_purge = False
        mock_query_object = mock_query.return_value
        mock_query_object.configure_mock(**{"count.return_value": 0})
        self.client._handle_existing_features(organism_entry)
        mock_query.assert_called_with(sequence.Feature, organism_id=organism_entry.organism_id)
        self.assertIn(unittest.mock.call.count(), mock_query_object.method_calls)
        self.assertEqual(len(mock_query_object.mock_calls), 1)

        # from-scratch import on full table without 'force' - should throw an exception
        self.client.fresh_load = True
        self.client.force_purge = False
        mock_query_object.reset_mock()
        mock_query_object.configure_mock(**{"count.return_value": 1})
        with self.assertRaises(iobase.DatabaseError):
            self.client._handle_existing_features(organism_entry)
        self.assertIn(unittest.mock.call.count(), mock_query_object.method_calls)
        self.assertEqual(len(mock_query_object.mock_calls), 1)

        # from-scratch import on full table with 'force' - should call delete
        self.client.fresh_load = True
        self.client.force_purge = True
        mock_query_object.reset_mock()
        mock_query_object.configure_mock(**{"count.return_value": 1})
        self.client._handle_existing_features(organism_entry)
        self.assertIn(unittest.mock.call.count(), mock_query_object.method_calls)
        self.assertIn(unittest.mock.call.delete(), mock_query_object.method_calls)
        self.assertEqual(len(mock_query_object.mock_calls), 2)

    @unittest.mock.patch("pychado.io.gff.GFFImportClient._check_if_gff_attributes_are_recognized")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_protein")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_relationships")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_publications")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_ontology_terms")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_cross_references")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_properties")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_synonyms")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_location")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_child_feature")
    def test_insert_gff_record_into_database(
            self, mock_handle_child: unittest.mock.Mock, mock_handle_location: unittest.mock.Mock,
            mock_handle_synonyms: unittest.mock.Mock, mock_handle_properties: unittest.mock.Mock,
            mock_handle_cross_references: unittest.mock.Mock, mock_handle_ontology_terms: unittest.mock.Mock,
            mock_handle_publications: unittest.mock.Mock, mock_handle_relationships: unittest.mock.Mock,
            mock_handle_protein: unittest.mock.Mock, mock_check_recognized: unittest.mock.Mock):
        # Tests the main function updating database tables according to the information in a GFF record
        self.assertIs(mock_handle_child, self.client._handle_child_feature)
        self.assertIs(mock_handle_location, self.client._handle_location)
        self.assertIs(mock_handle_synonyms, self.client._handle_synonyms)
        self.assertIs(mock_handle_properties, self.client._handle_properties)
        self.assertIs(mock_handle_cross_references, self.client._handle_cross_references)
        self.assertIs(mock_handle_ontology_terms, self.client._handle_ontology_terms)
        self.assertIs(mock_handle_publications, self.client._handle_publications)
        self.assertIs(mock_handle_relationships, self.client._handle_relationships)
        self.assertIs(mock_handle_protein, self.client._handle_protein)
        self.assertIs(mock_check_recognized, self.client._check_if_gff_attributes_are_recognized)

        organism_entry = organism.Organism(genus="", species="", abbreviation="testorganism", organism_id=1)
        all_features = {}
        mock_handle_child.return_value = None
        self.client._insert_gff_record_into_database(self.default_gff_record, organism_entry, all_features)
        mock_handle_child.assert_called_with(self.default_gff_record, organism_entry)
        mock_handle_location.assert_not_called()
        self.assertEqual(len(all_features), 0)

        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=1)
        mock_handle_child.return_value = feature_entry
        self.client._insert_gff_record_into_database(self.default_gff_record, organism_entry, all_features)
        mock_handle_child.assert_called_with(self.default_gff_record, organism_entry)
        mock_handle_location.assert_called_with(self.default_gff_record, feature_entry)
        mock_handle_synonyms.assert_called_with(self.default_gff_record, feature_entry)
        mock_handle_properties.assert_called_with(self.default_gff_record, feature_entry)
        mock_handle_cross_references.assert_called_with(self.default_gff_record, feature_entry)
        mock_handle_ontology_terms.assert_called_with(self.default_gff_record, feature_entry)
        mock_handle_publications.assert_called_with(self.default_gff_record, feature_entry)
        mock_handle_relationships.assert_called_with(self.default_gff_record, feature_entry, all_features)
        mock_handle_protein.assert_called_with(self.default_gff_record, feature_entry, organism_entry, all_features)
        mock_check_recognized.assert_called_with(self.default_gff_record)
        self.assertEqual(len(all_features), 1)

    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_feature")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._create_feature")
    def test_handle_child_feature(self, mock_create: unittest.mock.Mock, mock_insert: unittest.mock.Mock):
        # Tests the function transferring data from a GFF record to the 'feature' table
        self.assertIs(mock_create, self.client._create_feature)
        self.assertIs(mock_insert, self.client._handle_feature)
        organism_entry = organism.Organism(genus="", species="", abbreviation="testorganism", organism_id=1)
        feature_entry = self.client._handle_child_feature(self.default_gff_record, organism_entry)
        self.assertIsNone(feature_entry)
        mock_create.assert_not_called()

        self.default_gff_record.featuretype = "gene"
        mock_create.return_value = "AAA"
        self.client._handle_child_feature(self.default_gff_record, organism_entry)
        mock_create.assert_called_with(self.default_gff_record, 1, 41)
        mock_insert.assert_called_with("AAA", "testorganism")

    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_featureloc")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._create_featureloc")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient.query_first")
    def test_handle_location(self, mock_query: unittest.mock.Mock, mock_create: unittest.mock.Mock,
                             mock_insert: unittest.mock.Mock):
        # Tests the function transferring data from a GFF record to the 'feature' table
        self.assertIs(mock_query, self.client.query_first)
        self.assertIs(mock_create, self.client._create_featureloc)
        self.assertIs(mock_insert, self.client._handle_featureloc)

        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=1)
        mock_query.return_value = sequence.Feature(organism_id=11, type_id=300, uniquename="chromname", feature_id=2)

        featureloc_entry = self.client._handle_location(self.default_gff_record, feature_entry)
        mock_query.assert_called_with(sequence.Feature, organism_id=11, uniquename="testseqid")
        mock_create.assert_called_with(self.default_gff_record, 1, 2)
        mock_insert.assert_called()
        self.assertIsNotNone(featureloc_entry)

        mock_query.return_value = None
        featureloc_entry = self.client._handle_location(self.default_gff_record, feature_entry)
        self.assertIsNone(featureloc_entry)

        mock_query.return_value = sequence.Feature(organism_id=11, type_id=300, uniquename="chromname", feature_id=2)
        self.default_gff_record.seqid = self.default_gff_record.id
        featureloc_entry = self.client._handle_location(self.default_gff_record, feature_entry)
        self.assertIsNone(featureloc_entry)

    @unittest.mock.patch("pychado.io.gff.GFFImportClient._delete_feature_synonym")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_feature_synonym")
    @unittest.mock.patch("pychado.orm.sequence.FeatureSynonym")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_synonym")
    @unittest.mock.patch("pychado.orm.sequence.Synonym")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient.query_feature_synonym_by_type")
    def test_handle_synonyms(self, mock_query: unittest.mock.Mock, mock_synonym: unittest.mock.Mock,
                             mock_insert_synonym: unittest.mock.Mock, mock_feature_synonym: unittest.mock.Mock,
                             mock_insert_feature_synonym: unittest.mock.Mock,
                             mock_delete_feature_synonym: unittest.mock.Mock):
        # Tests the function transferring data from a GFF record to the 'feature_synonym' table
        self.assertIs(mock_query, self.client.query_feature_synonym_by_type)
        self.assertIs(mock_synonym, sequence.Synonym)
        self.assertIs(mock_insert_synonym, self.client._handle_synonym)
        self.assertIs(mock_feature_synonym, sequence.FeatureSynonym)
        self.assertIs(mock_insert_feature_synonym, self.client._handle_feature_synonym)
        self.assertIs(mock_delete_feature_synonym, self.client._delete_feature_synonym)

        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=1)
        mock_insert_synonym.return_value = utils.EmptyObject(synonym_id=12)

        all_synonyms = self.client._handle_synonyms(self.default_gff_record, feature_entry)
        mock_query.assert_called_with(1, [31, 32, 33])
        mock_synonym.assert_any_call(name="testalias", type_id=33, synonym_sgml="testalias")
        self.assertEqual(mock_insert_synonym.call_count, 2)
        mock_feature_synonym.assert_any_call(synonym_id=12, feature_id=1, pub_id=33, is_current=None)
        self.assertEqual(mock_insert_feature_synonym.call_count, 2)
        mock_delete_feature_synonym.assert_called()
        self.assertEqual(len(all_synonyms), 2)

        self.default_gff_record.attributes["synonym"] = "abcd;current=false"
        all_synonyms = self.client._handle_synonyms(self.default_gff_record, feature_entry)
        mock_synonym.assert_any_call(name="abcd", type_id=31, synonym_sgml="abcd")
        mock_feature_synonym.assert_any_call(synonym_id=12, feature_id=1, pub_id=33, is_current=False)
        self.assertEqual(len(all_synonyms), 3)

    @unittest.mock.patch("pychado.io.gff.GFFImportClient._delete_feature_pub")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_feature_pub")
    @unittest.mock.patch("pychado.orm.sequence.FeaturePub")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_pub")
    @unittest.mock.patch("pychado.orm.pub.Pub")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient.query_all")
    def test_handle_publications(self, mock_query: unittest.mock.Mock, mock_pub: unittest.mock.Mock,
                                 mock_insert_pub: unittest.mock.Mock, mock_featurepub: unittest.mock.Mock,
                                 mock_insert_feature_pub: unittest.mock.Mock,
                                 mock_delete_feature_pub: unittest.mock.Mock):
        # Tests the function transferring data from a GFF record to the 'feature_pub' table
        self.assertIs(mock_query, self.client.query_all)
        self.assertIs(mock_pub, pub.Pub)
        self.assertIs(mock_insert_pub, self.client._handle_pub)
        self.assertIs(mock_featurepub, sequence.FeaturePub)
        self.assertIs(mock_insert_feature_pub, self.client._handle_feature_pub)
        self.assertIs(mock_delete_feature_pub, self.client._delete_feature_pub)

        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        mock_insert_pub.return_value = utils.EmptyObject(pub_id=32, uniquename="")

        all_pubs = self.client._handle_publications(self.default_gff_record, feature_entry)
        mock_query.assert_called_with(sequence.FeaturePub, feature_id=12)
        mock_pub.assert_any_call(uniquename="PMID:12334", type_id=71)
        self.assertEqual(mock_insert_pub.call_count, 1)
        mock_featurepub.assert_any_call(feature_id=12, pub_id=32)
        self.assertEqual(mock_insert_feature_pub.call_count, 1)
        mock_delete_feature_pub.assert_called()
        self.assertEqual(len(all_pubs), 1)

    @unittest.mock.patch("pychado.io.gff.GFFImportClient._delete_feature_relationship")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_feature_relationship")
    @unittest.mock.patch("pychado.orm.sequence.FeatureRelationship")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient.query_first")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient.query_feature_relationship_by_type")
    def test_handle_relationships(self, mock_query: unittest.mock.Mock, mock_query_first: unittest.mock.Mock,
                                  mock_relationship: unittest.mock.Mock,
                                  mock_insert_relationship: unittest.mock.Mock,
                                  mock_delete_relationship: unittest.mock.Mock):
        # Tests the function transferring data from a GFF record to the 'feature_relationship' table
        self.assertIs(mock_query, self.client.query_feature_relationship_by_type)
        self.assertIs(mock_query_first, self.client.query_first)
        self.assertIs(mock_relationship, sequence.FeatureRelationship)
        self.assertIs(mock_insert_relationship, self.client._handle_feature_relationship)
        self.assertIs(mock_delete_relationship, self.client._delete_feature_relationship)

        subject_entry = sequence.Feature(organism_id=11, type_id=300, uniquename="testid", feature_id=33)
        object_entry = sequence.Feature(organism_id=11, type_id=400, uniquename="testparent", feature_id=44)
        mock_query_first.return_value = object_entry

        all_features = {object_entry.uniquename: object_entry}
        all_relationships = self.client._handle_relationships(self.default_gff_record, subject_entry, all_features)
        mock_query.assert_called_with(33, [62, 63])
        mock_query_first.assert_not_called()
        mock_relationship.assert_any_call(subject_id=33, object_id=44, type_id=62)
        self.assertEqual(mock_insert_relationship.call_count, 1)
        mock_delete_relationship.assert_called()
        self.assertEqual(len(all_relationships), 1)

        mock_relationship.reset_mock()
        mock_insert_relationship.reset_mock()
        mock_delete_relationship.reset_mock()
        all_features = {}
        all_relationships = self.client._handle_relationships(self.default_gff_record, subject_entry, all_features)
        mock_query.assert_called_with(33, [62, 63])
        mock_query_first.assert_called_with(sequence.Feature, organism_id=11, uniquename="testparent")
        mock_relationship.assert_any_call(subject_id=33, object_id=44, type_id=62)
        self.assertEqual(mock_insert_relationship.call_count, 1)
        mock_delete_relationship.assert_called()
        self.assertEqual(len(all_relationships), 1)

    @unittest.mock.patch("pychado.io.gff.GFFImportClient._delete_featureprop")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_featureprop")
    @unittest.mock.patch("pychado.orm.sequence.FeatureProp")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient.query_featureprop_by_type")
    def test_handle_properties(self, mock_query: unittest.mock.Mock, mock_prop: unittest.mock.Mock,
                               mock_insert_prop: unittest.mock.Mock, mock_delete_prop: unittest.mock.Mock):
        # Tests the function transferring data from a GFF record to the 'featureprop' table
        self.assertIs(mock_query, self.client.query_featureprop_by_type)
        self.assertIs(mock_prop, sequence.FeatureProp)
        self.assertIs(mock_insert_prop, self.client._handle_featureprop)
        self.assertIs(mock_delete_prop, self.client._delete_featureprop)

        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        all_properties = self.client._handle_properties(self.default_gff_record, feature_entry)
        mock_query.assert_called_with(12, [51, 52, 53])
        mock_prop.assert_any_call(feature_id=12, type_id=51, value="3.5")
        mock_prop.assert_any_call(feature_id=12, type_id=52, value="testsource")
        mock_prop.assert_any_call(feature_id=12, type_id=53, value="testnote")
        self.assertEqual(mock_insert_prop.call_count, 3)
        mock_delete_prop.assert_called()
        self.assertEqual(len(all_properties), 3)

    @unittest.mock.patch("pychado.io.gff.GFFImportClient._delete_feature_dbxref")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_feature_dbxref")
    @unittest.mock.patch("pychado.orm.sequence.FeatureDbxRef")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_dbxref")
    @unittest.mock.patch("pychado.orm.general.DbxRef")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_db")
    @unittest.mock.patch("pychado.orm.general.Db")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient.query_all")
    def test_handle_crossrefs(self, mock_query: unittest.mock.Mock, mock_db: unittest.mock.Mock,
                              mock_insert_db: unittest.mock.Mock, mock_dbxref: unittest.mock.Mock,
                              mock_insert_dbxref: unittest.mock.Mock, mock_feature_dbxref: unittest.mock.Mock,
                              mock_insert_feature_dbxref: unittest.mock.Mock,
                              mock_delete_feature_dbxref: unittest.mock.Mock):
        # Tests the function transferring data from a GFF record to the 'feature_dbxref' table
        self.assertIs(mock_query, self.client.query_all)
        self.assertIs(mock_db, general.Db)
        self.assertIs(mock_insert_db, self.client._handle_db)
        self.assertIs(mock_dbxref, general.DbxRef)
        self.assertIs(mock_insert_dbxref, self.client._handle_dbxref)
        self.assertIs(mock_feature_dbxref, sequence.FeatureDbxRef)
        self.assertIs(mock_insert_feature_dbxref, self.client._handle_feature_dbxref)
        self.assertIs(mock_delete_feature_dbxref, self.client._delete_feature_dbxref)

        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        mock_insert_db.return_value = utils.EmptyObject(db_id=44, name="")
        mock_insert_dbxref.return_value = utils.EmptyObject(dbxref_id=55, accession="", version="")

        all_crossrefs = self.client._handle_cross_references(self.default_gff_record, feature_entry)
        mock_query.assert_called_with(sequence.FeatureDbxRef, feature_id=12)
        mock_db.assert_any_call(name="testdb")
        mock_dbxref.assert_any_call(db_id=44, accession="testaccession", version="")
        mock_feature_dbxref.assert_any_call(feature_id=12, dbxref_id=55)
        self.assertEqual(mock_insert_db.call_count, 1)
        self.assertEqual(mock_insert_dbxref.call_count, 1)
        self.assertEqual(mock_insert_feature_dbxref.call_count, 1)
        mock_delete_feature_dbxref.assert_called()
        self.assertEqual(len(all_crossrefs), 1)

    @unittest.mock.patch("pychado.io.gff.GFFImportClient._delete_feature_cvterm")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._handle_feature_cvterm")
    @unittest.mock.patch("pychado.orm.sequence.FeatureCvTerm")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient.query_first")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient.query_feature_cvterm_by_ontology")
    def test_handle_ontology_terms(self, mock_query: unittest.mock.Mock, mock_query_first: unittest.mock.Mock,
                                   mock_feature_cvterm: unittest.mock.Mock,
                                   mock_insert_feature_cvterm: unittest.mock.Mock,
                                   mock_delete_feature_cvterm: unittest.mock.Mock):
        # Tests the function transferring data from a GFF record to the 'feature_cvterm' table
        self.assertIs(mock_query, self.client.query_feature_cvterm_by_ontology)
        self.assertIs(mock_query_first, self.client.query_first)
        self.assertIs(mock_feature_cvterm, sequence.FeatureCvTerm)
        self.assertIs(mock_insert_feature_cvterm, self.client._handle_feature_cvterm)
        self.assertIs(mock_delete_feature_cvterm, self.client._delete_feature_cvterm)

        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        mock_query_first.side_effect = [utils.EmptyObject(db_id=33),
                                        utils.EmptyObject(dbxref_id=44),
                                        utils.EmptyObject(cvterm_id=55, name="")]

        all_ontology_terms = self.client._handle_ontology_terms(self.default_gff_record, feature_entry)
        mock_query.assert_called_with(12, 131)
        mock_query_first.assert_any_call(general.Db, name="GO")
        mock_query_first.assert_any_call(general.DbxRef, db_id=33, accession="7890")
        mock_query_first.assert_any_call(cv.CvTerm, dbxref_id=44)
        self.assertEqual(mock_query_first.call_count, 3)
        mock_feature_cvterm.assert_any_call(feature_id=12, cvterm_id=55, pub_id=33)
        self.assertEqual(mock_insert_feature_cvterm.call_count, 1)
        mock_delete_feature_cvterm.assert_called()
        self.assertEqual(len(all_ontology_terms), 1)

    @unittest.mock.patch("pychado.io.gff.GFFImportClient._insert_gff_record_into_database")
    @unittest.mock.patch("gffutils.Feature")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient.query_first")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient.query_parent_features")
    def test_handle_protein(self, mock_query: unittest.mock.Mock, mock_query_first: unittest.mock.Mock,
                            mock_record: unittest.mock.Mock, mock_insert: unittest.mock.Mock):
        # Tests the function creating a new GFF record for a polypeptide and inserting it into the database
        self.assertIs(mock_query, self.client.query_parent_features)
        self.assertIs(mock_query_first, self.client.query_first)
        self.assertIs(mock_record, gffutils.Feature)
        self.assertIs(mock_insert, self.client._insert_gff_record_into_database)

        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        organism_entry = organism.Organism(genus="", species="", abbreviation="testorganism", organism_id=1)
        all_features = {}

        # No attribute "protein_source_id"
        self.client._handle_protein(self.default_gff_record, feature_entry, organism_entry, all_features)
        mock_query.assert_not_called()
        mock_query_first.assert_not_called()
        mock_record.assert_not_called()
        mock_insert.assert_not_called()

        # Attribute "protein_source_id" present; GFF record is mRNA
        self.default_gff_record.featuretype = "mRNA"
        self.default_gff_record.attributes["protein_source_id"] = "testid"
        mock_query_first.return_value = sequence.FeatureLoc(feature_id=1, srcfeature_id=2, fmin=300, fmax=400, strand=1)
        self.client._handle_protein(self.default_gff_record, feature_entry, organism_entry, all_features)
        mock_query.assert_not_called()
        mock_query_first.assert_called_with(sequence.FeatureLoc, feature_id=12)
        mock_record.assert_called_with(seqid="testseqid", source="testsource", start=301, end=400, strand="+",
                                       featuretype="polypeptide", id="testid", attributes={"Derives_from": "testname"})
        mock_insert.assert_called()

        # Attribute "protein_source_id" present; GFF record is not mRNA
        self.default_gff_record.featuretype = "CDS"
        mock_query_object = mock_query.return_value
        mock_query_object.configure_mock(**{"first.return_value": sequence.Feature(
            organism_id=11, type_id=200, uniquename="othername", feature_id=13)})
        self.client._handle_protein(self.default_gff_record, feature_entry, organism_entry, all_features)
        mock_query.assert_called_with(12, [62])
        mock_query_first.assert_called_with(sequence.FeatureLoc, feature_id=13)
        mock_record.assert_called_with(seqid="testseqid", source="testsource", start=301, end=400, strand="+",
                                       featuretype="polypeptide", id="testid", attributes={"Derives_from": "othername"})
        mock_insert.assert_called()

    @unittest.mock.patch("pychado.io.gff.GFFImportClient._mark_feature_as_obsolete")
    @unittest.mock.patch("pychado.io.gff.GFFImportClient._load_feature_names")
    def test_mark_obsolete_features(self, mock_load: unittest.mock.Mock, mock_mark: unittest.mock.Mock):
        # Tests the function that marks features as obsolete if they are not present in a given dictionary
        self.assertIs(mock_load, self.client._load_feature_names)
        self.assertIs(mock_mark, self.client._mark_feature_as_obsolete)
        organism_entry = organism.Organism(genus="", species="", abbreviation="testorganism", organism_id=1)
        mock_load.return_value = ["id1", "id2", "id3", "seq"]
        self.client._mark_obsolete_features(
            organism_entry, {"id3": sequence.Feature(organism_id=1, type_id=1, uniquename="")}, ["seq"])
        mock_load.assert_called_with(organism_entry)
        mock_mark.assert_any_call(organism_entry, "id2")
        self.assertEqual(mock_mark.call_count, 2)

    def test_check_if_gff_attributes_are_recognized(self):
        # Tests the function that checks if all attributes of a GFF record are recognized
        feature = self.default_gff_record
        recognized = self.client._check_if_gff_attributes_are_recognized(feature)
        self.assertTrue(recognized)
        feature.attributes["other_attribute"] = "other_value"
        recognized = self.client._check_if_gff_attributes_are_recognized(feature)
        self.assertFalse(recognized)

    def test_create_feature(self):
        # Tests the function that creates an entry for the 'feature' table
        feature = self.client._create_feature(self.default_gff_record, 3, 5)
        self.assertEqual(feature.organism_id, 3)
        self.assertEqual(feature.type_id, 5)
        self.assertEqual(feature.uniquename, "testid")
        self.assertEqual(feature.name, "testname")
        self.assertEqual(feature.residues, "MCRA")
        self.assertEqual(feature.seqlen, 4)

    def test_create_featureloc(self):
        # Tests the function that creates an entry for the 'featureloc' table
        featureloc = self.client._create_featureloc(self.default_gff_record, 3, 5)
        self.assertEqual(featureloc.feature_id, 3)
        self.assertEqual(featureloc.srcfeature_id, 5)
        self.assertEqual(featureloc.fmin, 0)
        self.assertEqual(featureloc.fmax, 30)
        self.assertEqual(featureloc.strand, 1)
        self.assertEqual(featureloc.phase, 2)

    def test_extract_gff_name(self):
        # Tests the function that extracts the name from a GFF record
        feature = gffutils.Feature()
        name = self.client._extract_gff_name(feature)
        self.assertIsNone(name)
        feature.attributes = {"Name": "testname"}
        name = self.client._extract_gff_name(feature)
        self.assertEqual(name, "testname")
        feature.attributes = {"Name": ["othername"]}
        name = self.client._extract_gff_name(feature)
        self.assertEqual(name, "othername")

    def test_extract_gff_size(self):
        # Tests the function that extracts the sequence length from a GFF record
        feature = gffutils.Feature()
        size = self.client._extract_gff_size(feature)
        self.assertIsNone(size)
        feature.attributes = {"size": "587"}
        size = self.client._extract_gff_size(feature)
        self.assertEqual(size, 587)

    def test_extract_gff_synonyms(self):
        # Tests the function that extracts the synonyms from a GFF record
        feature = gffutils.Feature(attributes={"Alias": "testalias;current=False",
                                               "previous_systematic_id": ["testsynonym"]})
        synonyms = self.client._extract_gff_synonyms(feature)
        self.assertEqual(len(synonyms), 2)
        self.assertEqual(len(synonyms["alias"]), 1)
        self.assertEqual(synonyms["alias"][0].value, "testalias")
        self.assertEqual(len(synonyms["previous_systematic_id"]), 1)
        self.assertEqual(synonyms["previous_systematic_id"][0].value, "testsynonym")

    def test_extract_gff_residues(self):
        # Tests the function that extracts an amino acid sequence from a GFF record
        feature = gffutils.Feature()
        residues = self.client._extract_gff_translation(feature)
        self.assertIsNone(residues)
        feature.attributes = {"translation": "actgaa"}
        residues = self.client._extract_gff_translation(feature)
        self.assertEqual(residues, "ACTGAA")
        feature.attributes = {"translation": ["cTTg"]}
        residues = self.client._extract_gff_translation(feature)
        self.assertEqual(residues, "CTTG")

    def test_extract_gff_relationships(self):
        # Tests the function that extracts feature relationships from a GFF record
        feature = gffutils.Feature(attributes={"Parent": "parentterm", "Derives_from": ["otherterm"],
                                               "other_key": "other_value"})
        relationships = self.client._extract_gff_relationships(feature)
        self.assertEqual(len(relationships), 2)
        self.assertEqual(relationships["part_of"], ["parentterm"])
        self.assertEqual(relationships["derives_from"], ["otherterm"])

    def test_extract_gff_properties(self):
        # Tests the function that extracts feature properties from a GFF record
        feature = gffutils.Feature(source="testsource", score="2.54",
                                   attributes={"Parent": "parentterm", "comment": ["first_value", "second_value"]})
        properties = self.client._extract_gff_properties(feature)
        self.assertEqual(len(properties), 3)
        self.assertEqual(properties["source"], ["testsource"])
        self.assertEqual(properties["score"], ["2.54"])
        self.assertEqual(properties["comment"], ["first_value", "second_value"])

    def test_extract_gff_crossrefs(self):
        # Tests the function that extracts database cross references from a GFF record
        feature = gffutils.Feature(attributes={"Dbxref": "Wikipedia:gene", "Ontology_term": ["GO:12345", "GO:67890"]})
        crossrefs = self.client._extract_gff_crossrefs(feature)
        self.assertEqual(len(crossrefs), 1)
        self.assertIn("Wikipedia:gene", crossrefs)

    def test_extract_gff_ontology_terms(self):
        # Tests the function that extracts ontology terms from a GFF record
        feature = gffutils.Feature(attributes={"Dbxref": "Wikipedia:gene", "Ontology_term": ["GO:12345", "GO:67890"]})
        ontology_terms = self.client._extract_gff_ontology_terms(feature)
        self.assertEqual(len(ontology_terms), 2)
        self.assertIn("GO:67890", ontology_terms)

    def test_extract_gff_publications(self):
        # Tests the function that extracts publications from a GFF record
        feature = gffutils.Feature(attributes={"literature": "PMID:12345"})
        publications = self.client._extract_gff_publications(feature)
        self.assertEqual(len(publications), 1)
        self.assertIn("PMID:12345", publications)

    def test_extract_gff_protein_source_id(self):
        # Tests the function that extracts the ID of a polypeptide from a GFF record
        feature = gffutils.Feature()
        protein_id = self.client._extract_protein_source_id(feature)
        self.assertIsNone(protein_id)
        feature.attributes = {"protein_source_id": "testid"}
        protein_id = self.client._extract_protein_source_id(feature)
        self.assertEqual(protein_id, "testid")

    def test_extract_gff_sequence_names(self):
        # Tests the function that extracts sequence names from a GFF file
        gff_file = os.path.join(data_dir, 'gff_without_fasta.gff3')
        self.assertTrue(os.path.exists(gff_file))
        gff_db = self.client._create_sqlite_db(gff_file)
        sequence_names = self.client._extract_gff_sequence_names(gff_db)
        self.assertIn("CM000574", sequence_names)
        gff_db_name = self.client._sqlite_databases[0]
        os.remove(gff_db_name)
        self.assertFalse(os.path.exists(gff_db_name))


class TestGFFExport(unittest.TestCase):
    """Tests various functions used to export a GFF file from a database"""

    @classmethod
    def setUpClass(cls):
        # Creates an instance of the base class to be tested and instantiates global attributes
        cls.client = gff.GFFExportClient("testuri", test_environment=True)
        cls.client._parent_terms = {
            "part_of": cv.CvTerm(cv_id=6, dbxref_id=62, name="part_of", cvterm_id=62, is_relationshiptype=1),
            "derives_from": cv.CvTerm(cv_id=6, dbxref_id=63, name="derives_from", cvterm_id=63, is_relationshiptype=1)
        }
        cls.client._top_level_term = cv.CvTerm(cv_id=11, dbxref_id=91, name="top_level_seq", cvterm_id=91)
        cls.client._parent_type_ids = [62, 63]
        cls.client._go_db = general.Db(db_id=131, name="GO")

    @unittest.mock.patch("pychado.io.gff.GFFExportClient._export_gff_record")
    @unittest.mock.patch("pychado.io.gff.GFFExportClient.query_child_features")
    def test_handle_child_features(self, mock_query: unittest.mock.Mock, mock_export: unittest.mock.Mock):
        # Tests the function that exports GFF records for the child features of a given feature
        self.assertIs(mock_query, self.client.query_child_features)
        self.assertIs(mock_export, self.client._export_gff_record)

        feature_entry = sequence.Feature(feature_id=77, organism_id=11, type_id=200, uniquename="parentid")
        childfeature_entry = sequence.Feature(feature_id=78, organism_id=11, type_id=300, uniquename="childid")
        derivedfeature_entry = sequence.Feature(feature_id=79, organism_id=11, type_id=400, uniquename="derivedid")
        mock_query_obj = mock_query.return_value
        mock_query_obj.configure_mock(**{"all.side_effect": [[childfeature_entry],
                                                             [childfeature_entry, derivedfeature_entry]]})

        self.client._handle_child_features(feature_entry, "testsequence", None)
        self.assertIn(unittest.mock.call(77, 62), mock_query.mock_calls)
        self.assertIn(unittest.mock.call(77, 63), mock_query.mock_calls)
        self.assertEqual(mock_query.call_count, 2)
        self.assertIn(unittest.mock.call(childfeature_entry, "testsequence", {"part_of": "parentid"}, None),
                      mock_export.mock_calls)
        self.assertIn(unittest.mock.call(childfeature_entry, "testsequence", {"derives_from": "parentid"}, None),
                      mock_export.mock_calls)
        self.assertIn(unittest.mock.call(derivedfeature_entry, "testsequence", {"derives_from": "parentid"}, None),
                      mock_export.mock_calls)
        self.assertEqual(mock_export.call_count, 3)

    @unittest.mock.patch("pychado.io.fasta.FastaExportClient")
    @unittest.mock.patch("pychado.io.gff.GFFExportClient._append_fasta")
    def test_export_fasta(self, mock_append: unittest.mock.Mock, mock_fasta: unittest.mock.Mock):
        # Tests the export of FASTA sequences along with a GFF file
        self.assertIs(mock_append, self.client._append_fasta)
        self.assertIs(mock_fasta, fasta.FastaExportClient)

        # Output FASTA in separate file
        self.client._export_fasta("testgff", "testfasta", "testorganism")
        mock_fasta.assert_called_with("testuri", False)
        self.assertIn(unittest.mock.call().export("testfasta", "testorganism", "contigs", ""), mock_fasta.mock_calls)
        mock_append.assert_not_called()

        # Append FASTA to GFF file
        mock_fasta.reset_mock()
        mock_append.reset_mock()
        self.client._export_fasta("testgff", "", "testorganism")
        mock_fasta.assert_called_with("testuri", False)
        mock_append.assert_called()

    def test_append_fasta(self):
        # Tests the function joining a GFF file with a FASTA file
        gff_file = os.path.join(data_dir, 'gff_without_fasta.gff3')
        fasta_file = os.path.join(data_dir, 'fasta_only.fa')
        joined_file = tempfile.mkstemp()[1]
        shutil.copy(gff_file, joined_file)
        actual_joined_file = os.path.join(data_dir, 'gff_with_fasta.gff3')
        self.client._append_fasta(joined_file, fasta_file)
        self.assertTrue(filecmp.cmp(joined_file, actual_joined_file))
        os.remove(joined_file)

    def test_write_gff_header(self):
        # Tests the correct creation of GFF file headers
        header_file = tempfile.mkstemp()[1]
        header_file_handle = utils.open_file_write(header_file)
        self.client._write_gff_header(header_file_handle, [sequence.Feature(feature_id=77, organism_id=11, type_id=200,
                                                                            seqlen=11697295, uniquename="CM000574")])
        utils.close(header_file_handle)
        actual_header_file = os.path.join(data_dir, 'gff_header.gff3')
        self.assertTrue(filecmp.cmp(header_file, actual_header_file))
        os.remove(header_file)

    def test_print_gff_record(self):
        # Tests the correct printing of GFF records to file
        gff_record = gffutils.Feature(seqid="CM000574", id="FGSG_11579", source="chado", featuretype="gene",
                                      start=1517, end=2509, strand="+", attributes={"ID": ["FGSG_11579"]})
        file = tempfile.mkstemp()[1]
        file_handle = utils.open_file_write(file)
        self.client._print_gff_record(gff_record, file_handle)
        utils.close(file_handle)
        actual_file = os.path.join(data_dir, 'gff_line.gff3')
        self.assertTrue(filecmp.cmp(file, actual_file))
        os.remove(file)

    @unittest.mock.patch("pychado.io.gff.GFFExportClient.query_first")
    def test_create_gff_record(self, mock_query: unittest.mock.Mock):
        # Tests the function that creates a GFF record
        self.assertIs(mock_query, self.client.query_first)
        feature_entry = sequence.Feature(feature_id=77, organism_id=11, type_id=200, seqlen=66, uniquename="testid",
                                         name="testname")

        # Create GFF record for top-level feature
        mock_query.return_value = None
        gff_record = self.client._create_gff_record(feature_entry, "testsequence")
        self.assertEqual(gff_record.seqid, "testsequence")
        self.assertEqual(gff_record.id, "testid")
        self.assertEqual(gff_record.start, 1)
        self.assertEqual(gff_record.end, 66)
        self.assertEqual(gff_record.strand, ".")
        self.assertEqual(gff_record.frame, ".")
        self.assertEqual(gff_record.attributes["ID"], ["testid"])
        self.assertEqual(gff_record.attributes["Name"], ["testname"])

        # Create GFF record for feature located on a sequence
        mock_query.return_value = sequence.FeatureLoc(feature_id=1, srcfeature_id=2, fmin=10, fmax=100, strand=1,
                                                      phase=2)
        gff_record = self.client._create_gff_record(feature_entry, "testsequence")
        self.assertEqual(gff_record.seqid, "testsequence")
        self.assertEqual(gff_record.id, "testid")
        self.assertEqual(gff_record.start, 11)
        self.assertEqual(gff_record.end, 100)
        self.assertEqual(gff_record.strand, "+")
        self.assertEqual(gff_record.frame, "2")

    @unittest.mock.patch("pychado.io.gff.GFFExportClient.query_parent_features")
    def test_has_feature_parents(self, mock_query: unittest.mock.Mock):
        # Tests the function that checks if a feature entry has parents
        self.assertIs(mock_query, self.client.query_parent_features)
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testid", feature_id=77)
        mock_query_obj = mock_query.return_value
        mock_query_obj.configure_mock(**{"first.return_value": None})
        has_parents = self.client._has_feature_parents(feature_entry)
        mock_query.assert_called_with(77, [62, 63])
        self.assertFalse(has_parents)
        mock_query_obj.configure_mock(**{"first.return_value": sequence.Feature(
            organism_id=11, type_id=300, uniquename="parentid", feature_id=88)})
        has_parents = self.client._has_feature_parents(feature_entry)
        self.assertTrue(has_parents)

    @unittest.mock.patch("pychado.io.gff.GFFExportClient.query_first")
    def test_extract_feature_type(self, mock_query: unittest.mock.Mock):
        # Tests the function that extracts the type of a feature entry from the relevant database table
        self.assertIs(mock_query, self.client.query_first)
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testid", feature_id=77)
        mock_query.return_value = cv.CvTerm(cv_id=1, dbxref_id=2, name="testtype")
        featuretype = self.client._extract_feature_type(feature_entry)
        mock_query.assert_called_with(cv.CvTerm, cvterm_id=200)
        self.assertEqual(featuretype, "testtype")

    @unittest.mock.patch("pychado.io.gff.GFFExportClient.query_feature_synonyms")
    def test_extract_feature_synonyms(self, mock_query: unittest.mock.Mock):
        # Tests the function that extracts the synonyms of a feature entry from the relevant database table
        self.assertIs(mock_query, self.client.query_feature_synonyms)
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testid", feature_id=77)
        mock_query_obj = mock_query.return_value
        mock_query_obj.configure_mock(**{"all.return_value": [("sometype", "somename"), ("sometype", "othername")]})
        synonyms = self.client._extract_feature_synonyms(feature_entry)
        mock_query.assert_called_with(77)
        self.assertEqual(synonyms, {"sometype": ["somename", "othername"]})

    @unittest.mock.patch("pychado.io.gff.GFFExportClient.query_feature_properties")
    def test_extract_feature_properties(self, mock_query: unittest.mock.Mock):
        # Tests the function that extracts the synonyms of a feature entry from the relevant database table
        self.assertIs(mock_query, self.client.query_feature_properties)
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testid", feature_id=77)
        mock_query_obj = mock_query.return_value
        mock_query_obj.configure_mock(**{"all.return_value": [("somekey", "somevalue"), ("somekey", "othervalue"),
                                                              ("otherkey", "yetanothervalue")]})
        properties = self.client._extract_feature_properties(feature_entry)
        mock_query.assert_called_with(77)
        self.assertEqual(properties, {"somekey": ["somevalue", "othervalue"], "otherkey": ["yetanothervalue"]})

    @unittest.mock.patch("pychado.io.gff.GFFExportClient.query_feature_pubs")
    def test_extract_feature_publications(self, mock_query: unittest.mock.Mock):
        # Tests the function that extracts the publications of a feature entry from the relevant database table
        self.assertIs(mock_query, self.client.query_feature_pubs)
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testid", feature_id=77)
        mock_query_obj = mock_query.return_value
        mock_query_obj.configure_mock(**{"all.return_value": [("somepublication", ), ("otherpublication", )]})
        publications = self.client._extract_feature_publications(feature_entry)
        mock_query.assert_called_with(77)
        self.assertEqual(publications, ["somepublication", "otherpublication"])

    @unittest.mock.patch("pychado.io.gff.GFFExportClient.query_feature_dbxrefs")
    def test_extract_feature_dbxrefs(self, mock_query: unittest.mock.Mock):
        # Tests the function that extracts the cross references of a feature entry from the relevant database table
        self.assertIs(mock_query, self.client.query_feature_dbxrefs)
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testid", feature_id=77)
        mock_query_obj = mock_query.return_value
        mock_query_obj.configure_mock(**{"all.return_value": [("somedb", "someacc",), ("otherdb", "otheracc")]})
        dbxrefs = self.client._extract_feature_cross_references(feature_entry)
        mock_query.assert_called_with(77)
        self.assertEqual(dbxrefs, ["somedb:someacc", "otherdb:otheracc"])

    @unittest.mock.patch("pychado.io.gff.GFFExportClient.query_feature_ontology_terms")
    def test_extract_feature_ontology_terms(self, mock_query: unittest.mock.Mock):
        # Tests the function that extracts the ontology terms of a feature entry from the relevant database table
        self.assertIs(mock_query, self.client.query_feature_ontology_terms)
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testid", feature_id=77)
        mock_query_obj = mock_query.return_value
        mock_query_obj.configure_mock(**{"all.return_value": [("GO", "12345"), ("SO", "54321")]})
        ontology_terms = self.client._extract_feature_ontology_terms(feature_entry)
        mock_query.assert_called_with(77, 131)
        self.assertEqual(ontology_terms, ["GO:12345", "SO:54321"])

    def test_add_gff_featuretype(self):
        # Tests the function that adds the 'type' and the attribute 'translation' to a GFF record
        gff_record = gffutils.Feature()
        self.client._add_gff_featuretype(gff_record, "gene", "MKGHU")
        self.assertEqual(gff_record.featuretype, "gene")
        self.assertNotIn("translation", gff_record.attributes)
        self.client._add_gff_featuretype(gff_record, "polypeptide", "MKGHU")
        self.assertEqual(gff_record.featuretype, "polypeptide")
        self.assertEqual(gff_record.attributes["translation"], ["MKGHU"])

    def test_add_gff_synonyms(self):
        # Tests the function that adds the attribute 'Alias' and various related attributes to a GFF record
        gff_record = gffutils.Feature()
        self.client._add_gff_synonyms(gff_record, {"alias": ["testalias", "otheralias"], "synonym": ["testsynonym"],
                                                   "otherkey": ["othervalue"]})
        self.assertEqual(gff_record.attributes["Alias"], ["testalias", "otheralias"])
        self.assertEqual(gff_record.attributes["synonym"], ["testsynonym"])
        self.assertNotIn("otherkey", gff_record.attributes)

    def test_add_gff_properties(self):
        # Tests the function that adds the 'source', 'score' and various attributes to a GFF record
        gff_record = gffutils.Feature()
        self.client._add_gff_properties(
            gff_record, {"source": ["testsource"], "score": ["testscore"], "comment": ["testcomment", "othercomment"],
                         "otherkey": ["othervalue"]})
        self.assertEqual(gff_record.source, "testsource")
        self.assertEqual(gff_record.score, "testscore")
        self.assertEqual(gff_record.attributes["comment"], ["testcomment", "othercomment"])
        self.assertNotIn("otherkey", gff_record.attributes)

    def test_add_gff_publications(self):
        # Tests the function that adds the attribute 'literature' to a GFF record
        gff_record = gffutils.Feature()
        self.client._add_gff_publications(gff_record, ["testpub"])
        self.assertEqual(gff_record.attributes["literature"], ["testpub"])

    def test_add_gff_cross_references(self):
        # Tests the function that adds the attribute 'Dbxref' to a GFF record
        gff_record = gffutils.Feature()
        self.client._add_gff_cross_references(gff_record, ["testdbxref", "otherdbxref"])
        self.assertEqual(gff_record.attributes["Dbxref"], ["testdbxref", "otherdbxref"])

    def test_add_gff_ontology_terms(self):
        # Tests the function that adds the attribute 'Ontology_term' to a GFF record
        gff_record = gffutils.Feature()
        self.client._add_gff_ontology_terms(gff_record, ["GO:12345"])
        self.assertEqual(gff_record.attributes["Ontology_term"], ["GO:12345"])

    def test_add_gff_relationships(self):
        # Tests the function that adds the attributes 'Parent' and 'Derives_from' to a GFF record
        gff_record = gffutils.Feature()
        self.client._add_gff_relationships(gff_record, {"part_of": "feature1", "derives_from": "feature2",
                                                        "orthologous_to": "other_feature"})
        self.assertEqual(gff_record.attributes["Parent"], ["feature1"])
        self.assertEqual(gff_record.attributes["Derives_from"], ["feature2"])
        self.assertNotIn("orthologous_to", gff_record.attributes)


class TestGFFFunctions(unittest.TestCase):
    """Tests various general functions used in connection with GFF import/export"""

    @classmethod
    def setUpClass(cls):
        # Creates an instance of the base class to be tested
        cls.client = gff.GFFClient()

    def test_parse_artemis_gff_attribute(self):
        # Tests the parsing of complex GFF attributes
        text_attribute = "sar1;current=false"
        parsed_attribute = self.client.parse_artemis_gff_attribute(text_attribute)
        self.assertEqual(parsed_attribute.value, "sar1")
        self.assertEqual(len(parsed_attribute.list_params), 1)
        self.assertEqual(len(parsed_attribute.dict_params), 1)
        self.assertIn("current", parsed_attribute.dict_params)
        self.assertFalse(parsed_attribute.dict_params["current"])

        text_attribute = "term=reticulocyte binding protein 2b, putative"
        parsed_attribute = self.client.parse_artemis_gff_attribute(text_attribute)
        self.assertEqual(parsed_attribute.value, "reticulocyte binding protein 2b, putative")
        self.assertEqual(len(parsed_attribute.list_params), 0)
        self.assertEqual(len(parsed_attribute.dict_params), 1)

        text_attribute = "signalp;;query 1-22;cleavage_site_probability=0.387"
        parsed_attribute = self.client.parse_artemis_gff_attribute(text_attribute)
        self.assertEqual(parsed_attribute.value, "signalp")
        self.assertEqual(len(parsed_attribute.list_params), 2)
        self.assertEqual(len(parsed_attribute.dict_params), 1)
        self.assertIn("query 1-22", parsed_attribute.list_params)
        self.assertIn("cleavage_site_probability", parsed_attribute.dict_params)
        self.assertEqual(parsed_attribute.dict_params["cleavage_site_probability"], 0.387)

    def test_convert_strand(self):
        # Tests the function converting the 'strand' attribute from string notation to integer notation
        gff_strand = "+"
        chado_strand = self.client.convert_strand(gff_strand)
        self.assertEqual(chado_strand, 1)
        gff_strand = "-"
        chado_strand = self.client.convert_strand(gff_strand)
        self.assertEqual(chado_strand, -1)
        gff_strand = "something_else"
        chado_strand = self.client.convert_strand(gff_strand)
        self.assertIsNone(chado_strand)

    def test_back_convert_strand(self):
        # Tests the function converting the 'strand' attribute from integer notation to string notation
        chado_strand = 1
        gff_strand = self.client.back_convert_strand(chado_strand)
        self.assertEqual(gff_strand, "+")
        chado_strand = -5
        gff_strand = self.client.back_convert_strand(chado_strand)
        self.assertEqual(gff_strand, "-")
        chado_strand = None
        gff_strand = self.client.back_convert_strand(chado_strand)
        self.assertEqual(gff_strand, ".")

    def test_convert_frame(self):
        # Tests the function converting the 'frame' attribute from string notation to integer notation
        gff_frame = "."
        chado_frame = self.client.convert_frame(gff_frame)
        self.assertIsNone(chado_frame)
        gff_frame = "2"
        chado_frame = self.client.convert_frame(gff_frame)
        self.assertEqual(chado_frame, 2)
        gff_frame = "3"
        chado_frame = self.client.convert_frame(gff_frame)
        self.assertIsNone(chado_frame)

    def test_back_convert_frame(self):
        # Tests the function converting the 'frame' attribute from integer notation to string notation
        chado_frame = 1
        gff_frame = self.client.back_convert_frame(chado_frame)
        self.assertEqual(gff_frame, "1")
        chado_frame = None
        gff_frame = self.client.back_convert_frame(chado_frame)
        self.assertEqual(gff_frame, ".")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
