import unittest.mock
import os
import tempfile
import filecmp
from .. import utils
from ..io import iobase, gaf
from ..orm import general, cv, pub, organism, sequence

modules_dir = os.path.dirname(os.path.abspath(gaf.__file__))
data_dir = os.path.abspath(os.path.join(modules_dir, '..', 'tests', 'data'))


class TestGAFImport(unittest.TestCase):
    """Tests various functions used to load a GFF file into a database"""

    @classmethod
    def setUpClass(cls):
        # Creates an instance of the base class to be tested and instantiates global attributes
        cls.client = gaf.GAFImportClient("testuri", test_environment=True)
        cls.client.printer = utils.VerbosePrinter(False)
        cls.client._date_term = cv.CvTerm(cv_id=11, dbxref_id=91, name="date", cvterm_id=91)
        cls.client._evidence_term = cv.CvTerm(cv_id=11, dbxref_id=92, name="evidence", cvterm_id=92)
        cls.client._synonym_term = cv.CvTerm(cv_id=11, dbxref_id=93, name="synonym", cvterm_id=93)
        cls.client._assigned_by_term = cv.CvTerm(cv_id=11, dbxref_id=94, name="assigned_by", cvterm_id=94)
        cls.client._default_pub = pub.Pub(uniquename="null", type_id=71, pub_id=33)
        cls.client._go_db = general.Db(name="GO", db_id=44)

    def setUp(self):
        # Creates a default GAF record
        self.default_gaf_record = {'DB': 'testdb', 'DB_Object_ID': 'testname', 'DB_Object_Symbol': 'testsymbol',
                                   'Qualifier': [''], 'GO_ID': 'GO:12345', 'DB:Reference': ['testdb:testaccession'],
                                   'Evidence': 'TAS', 'With': ['evidencedb:evidenceaccession'], 'Aspect': 'C',
                                   'DB_Object_Name': 'testproduct', 'Synonym': ['S1', 'S2'],
                                   'DB_Object_Type': 'transcript', 'Taxon_ID': ['testtaxon'],
                                   'Date': 'testdate', 'Assigned_By': 'assigning_db'}

    @unittest.mock.patch("pychado.io.gaf.GAFImportClient.query_first")
    def test_load_feature(self, mock_query: unittest.mock.Mock):
        # Tests the function loading the entry from the 'feature' table that corresponds to a GAF record
        self.assertIs(mock_query, self.client.query_first)
        organism_entry = organism.Organism(genus="", species="", abbreviation="testorganism", organism_id=1)
        self.client._load_feature(self.default_gaf_record, organism_entry)
        mock_query.assert_called_with(sequence.Feature, organism_id=1, uniquename="testname")

    def test_handle_name(self):
        # Tests the function that updates a feature name according to a GAF record
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        self.client._handle_name(self.default_gaf_record, feature_entry)
        self.assertEqual(feature_entry.name, "testsymbol")
        self.default_gaf_record["DB_Object_Symbol"] = "testname"
        self.client._handle_name(self.default_gaf_record, feature_entry)
        self.assertNotEqual(feature_entry.name, "testname")

    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_feature_synonym")
    @unittest.mock.patch("pychado.orm.sequence.FeatureSynonym")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_synonym")
    @unittest.mock.patch("pychado.orm.sequence.Synonym")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient.query_feature_synonym_by_type")
    def test_handle_synonyms(self, mock_query: unittest.mock.Mock, mock_synonym: unittest.mock.Mock,
                             mock_insert_synonym: unittest.mock.Mock, mock_feature_synonym: unittest.mock.Mock,
                             mock_insert_feature_synonym: unittest.mock.Mock):
        # Tests the function transferring data from a GAF record to the 'feature_synonym' table
        self.assertIs(mock_query, self.client.query_feature_synonym_by_type)
        self.assertIs(mock_synonym, sequence.Synonym)
        self.assertIs(mock_insert_synonym, self.client._handle_synonym)
        self.assertIs(mock_feature_synonym, sequence.FeatureSynonym)
        self.assertIs(mock_insert_feature_synonym, self.client._handle_feature_synonym)

        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        mock_query.return_value.configure_mock(**{"all.return_value": []})
        mock_insert_synonym.return_value = utils.EmptyObject(synonym_id=99)

        all_feature_synonyms = self.client._handle_synonyms(self.default_gaf_record, feature_entry)
        mock_query.assert_called_with(12, [93])
        mock_synonym.assert_any_call(name="S1", type_id=93, synonym_sgml="S1")
        mock_feature_synonym.assert_any_call(synonym_id=99, feature_id=12, pub_id=33)
        self.assertEqual(len(all_feature_synonyms), 2)

    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_feature_cvterm")
    @unittest.mock.patch("pychado.orm.sequence.FeatureCvTerm")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_pub")
    @unittest.mock.patch("pychado.orm.pub.Pub")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._extract_primary_publication")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient.query_first")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient.query_feature_cvterm_by_ontology")
    def test_handle_ontology_term(self, mock_query: unittest.mock.Mock, mock_query_first: unittest.mock.Mock,
                                  mock_extract: unittest.mock.Mock,
                                  mock_pub: unittest.mock.Mock, mock_insert_pub: unittest.mock.Mock,
                                  mock_feature_cvterm: unittest.mock.Mock,
                                  mock_insert_feature_cvterm: unittest.mock.Mock):
        # Tests the function transferring data from a GAF record to the 'feature_cvterm' table
        self.assertIs(mock_query, self.client.query_feature_cvterm_by_ontology)
        self.assertIs(mock_query_first, self.client.query_first)
        self.assertIs(mock_extract, self.client._extract_primary_publication)
        self.assertIs(mock_pub, pub.Pub)
        self.assertIs(mock_insert_pub, self.client._handle_pub)
        self.assertIs(mock_feature_cvterm, sequence.FeatureCvTerm)
        self.assertIs(mock_insert_feature_cvterm, self.client._handle_feature_cvterm)

        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        mock_extract.return_value = "PMID:12345"
        mock_query_first.side_effect = [utils.EmptyObject(db_id=33),
                                        utils.EmptyObject(dbxref_id=44),
                                        utils.EmptyObject(cvterm_id=55, name="")]
        mock_insert_pub.return_value = utils.EmptyObject(pub_id=66)

        ontology_term = self.client._handle_ontology_term(self.default_gaf_record, feature_entry)
        mock_query_first.assert_any_call(general.DbxRef, db_id=33, accession="12345")
        mock_query_first.assert_any_call(cv.CvTerm, dbxref_id=44)
        self.assertEqual(mock_query_first.call_count, 3)
        mock_pub.assert_any_call(uniquename="PMID:12345", type_id=71)
        self.assertEqual(mock_insert_pub.call_count, 1)
        mock_query.assert_called_with(12, 33)
        mock_feature_cvterm.assert_any_call(feature_id=12, cvterm_id=55, pub_id=66, is_not=False)
        self.assertEqual(mock_insert_feature_cvterm.call_count, 1)
        self.assertIsNotNone(ontology_term)

    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_feature_cvterm")
    @unittest.mock.patch("pychado.orm.sequence.FeatureCvTerm")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_pub")
    @unittest.mock.patch("pychado.orm.pub.Pub")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_cvterm")
    @unittest.mock.patch("pychado.orm.cv.CvTerm")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_cv")
    @unittest.mock.patch("pychado.orm.cv.Cv")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_dbxref")
    @unittest.mock.patch("pychado.orm.general.DbxRef")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_db")
    @unittest.mock.patch("pychado.orm.general.Db")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._extract_primary_publication")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient.query_feature_cvterm_by_ontology")
    def test_handle_product_term(self, mock_query: unittest.mock.Mock, mock_extract: unittest.mock.Mock,
                                 mock_db: unittest.mock.Mock, mock_insert_db: unittest.mock.Mock,
                                 mock_dbxref: unittest.mock.Mock, mock_insert_dbxref: unittest.mock.Mock,
                                 mock_cv: unittest.mock.Mock, mock_insert_cv: unittest.mock.Mock,
                                 mock_cvterm: unittest.mock.Mock, mock_insert_cvterm: unittest.mock.Mock,
                                 mock_pub: unittest.mock.Mock, mock_insert_pub: unittest.mock.Mock,
                                 mock_feature_cvterm: unittest.mock.Mock,
                                 mock_insert_feature_cvterm: unittest.mock.Mock):
        # Tests the function transferring data from a GAF record to the 'feature_cvterm' table
        self.assertIs(mock_query, self.client.query_feature_cvterm_by_ontology)
        self.assertIs(mock_extract, self.client._extract_primary_publication)
        self.assertIs(mock_db, general.Db)
        self.assertIs(mock_insert_db, self.client._handle_db)
        self.assertIs(mock_dbxref, general.DbxRef)
        self.assertIs(mock_insert_dbxref, self.client._handle_dbxref)
        self.assertIs(mock_cv, cv.Cv)
        self.assertIs(mock_insert_cv, self.client._handle_cv)
        self.assertIs(mock_cvterm, cv.CvTerm)
        self.assertIs(mock_insert_cvterm, self.client._handle_cvterm)
        self.assertIs(mock_pub, pub.Pub)
        self.assertIs(mock_insert_pub, self.client._handle_pub)
        self.assertIs(mock_feature_cvterm, sequence.FeatureCvTerm)
        self.assertIs(mock_insert_feature_cvterm, self.client._handle_feature_cvterm)

        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        mock_extract.return_value = "PMID:12345"
        mock_insert_db.return_value = utils.EmptyObject(db_id=22, name="")
        mock_insert_dbxref.return_value = utils.EmptyObject(dbxref_id=33)
        mock_insert_cv.return_value = utils.EmptyObject(cv_id=44, name="")
        mock_insert_cvterm.return_value = utils.EmptyObject(cvterm_id=55, name="")
        mock_insert_pub.return_value = utils.EmptyObject(pub_id=66)

        product_term = self.client._handle_product_term(self.default_gaf_record, feature_entry)
        mock_db.assert_called_with(name="PRODUCT")
        mock_dbxref.assert_called_with(db_id=22, accession="testproduct")
        mock_cv.assert_called_with(name="genedb_products")
        mock_cvterm.assert_called_with(cv_id=44, dbxref_id=33, name="testproduct")
        mock_pub.assert_called_with(uniquename="PMID:12345", type_id=71)
        mock_query.assert_called_with(12, 22)
        mock_feature_cvterm.assert_called_with(feature_id=12, cvterm_id=55, pub_id=66)

        mock_insert_db.assert_called()
        mock_insert_dbxref.assert_called()
        mock_insert_cv.assert_called()
        mock_insert_cvterm.assert_called()
        mock_insert_pub.assert_called()
        mock_insert_feature_cvterm.assert_called()
        self.assertIsNotNone(product_term)

    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_feature_cvtermprop")
    @unittest.mock.patch("pychado.orm.sequence.FeatureCvTermProp")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient.query_all")
    def test_handle_properties(self, mock_query: unittest.mock.Mock, mock_prop: unittest.mock.Mock,
                               mock_insert_prop: unittest.mock.Mock):
        # Tests the function transferring data from a GAF record to the 'feature_cvtermprop' table
        self.assertIs(mock_query, self.client.query_all)
        self.assertIs(mock_prop, sequence.FeatureCvTermProp)
        self.assertIs(mock_insert_prop, self.client._handle_feature_cvtermprop)

        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=1, cvterm_id=2, pub_id=3, feature_cvterm_id=4)

        all_properties = self.client._handle_properties(self.default_gaf_record, feature_cvterm_entry, feature_entry)
        mock_query.assert_called_with(sequence.FeatureCvTermProp, feature_cvterm_id=4)
        mock_prop.assert_any_call(feature_cvterm_id=4, type_id=91, value="testdate")
        mock_prop.assert_any_call(feature_cvterm_id=4, type_id=92, value="Traceable Author Statement")
        mock_prop.assert_any_call(feature_cvterm_id=4, type_id=94, value="assigning_db")
        self.assertEqual(mock_insert_prop.call_count, 3)
        self.assertEqual(len(all_properties), 3)

    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_feature_cvterm_dbxref")
    @unittest.mock.patch("pychado.orm.sequence.FeatureCvTermDbxRef")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_dbxref")
    @unittest.mock.patch("pychado.orm.general.DbxRef")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_db")
    @unittest.mock.patch("pychado.orm.general.Db")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._extract_cross_references")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient.query_all")
    def test_handle_crossrefs(self, mock_query: unittest.mock.Mock, mock_extract: unittest.mock.Mock,
                              mock_db: unittest.mock.Mock, mock_insert_db: unittest.mock.Mock,
                              mock_dbxref: unittest.mock.Mock, mock_insert_dbxref: unittest.mock.Mock,
                              mock_feature_cvterm_dbxref: unittest.mock.Mock,
                              mock_insert_feature_cvterm_dbxref: unittest.mock.Mock):
        # Tests the function transferring data from a GAF record to the 'feature_cvterm_dbxref' table
        self.assertIs(mock_query, self.client.query_all)
        self.assertIs(mock_extract, self.client._extract_cross_references)
        self.assertIs(mock_db, general.Db)
        self.assertIs(mock_insert_db, self.client._handle_db)
        self.assertIs(mock_dbxref, general.DbxRef)
        self.assertIs(mock_insert_dbxref, self.client._handle_dbxref)
        self.assertIs(mock_feature_cvterm_dbxref, sequence.FeatureCvTermDbxRef)
        self.assertIs(mock_insert_feature_cvterm_dbxref, self.client._handle_feature_cvterm_dbxref)

        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=1, cvterm_id=2, pub_id=3, feature_cvterm_id=4)
        mock_extract.return_value = ["evidencedb:evidenceaccession"]
        mock_insert_db.return_value = utils.EmptyObject(db_id=44, name="")
        mock_insert_dbxref.return_value = utils.EmptyObject(dbxref_id=55, accession="", version="")

        all_crossrefs = self.client._handle_crossrefs(self.default_gaf_record, feature_cvterm_entry, feature_entry)
        mock_query.assert_called_with(sequence.FeatureCvTermDbxRef, feature_cvterm_id=4)
        mock_db.assert_any_call(name="evidencedb")
        mock_dbxref.assert_any_call(db_id=44, accession="evidenceaccession", version="")
        mock_feature_cvterm_dbxref.assert_any_call(feature_cvterm_id=4, dbxref_id=55)
        self.assertEqual(mock_insert_db.call_count, 1)
        self.assertEqual(mock_insert_dbxref.call_count, 1)
        self.assertEqual(mock_insert_feature_cvterm_dbxref.call_count, 1)
        self.assertEqual(len(all_crossrefs), 1)

    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_feature_cvterm_pub")
    @unittest.mock.patch("pychado.orm.sequence.FeatureCvTermPub")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_pub")
    @unittest.mock.patch("pychado.orm.pub.Pub")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._extract_secondary_publications")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient.query_all")
    def test_handle_publications(self, mock_query: unittest.mock.Mock, mock_extract: unittest.mock.Mock,
                                 mock_pub: unittest.mock.Mock, mock_insert_pub: unittest.mock.Mock,
                                 mock_feature_cvterm_pub: unittest.mock.Mock,
                                 mock_insert_feature_cvterm_pub: unittest.mock.Mock):
        # Tests the function transferring data from a GAF record to the 'feature_cvterm_pub' table
        self.assertIs(mock_query, self.client.query_all)
        self.assertIs(mock_extract, self.client._extract_secondary_publications)
        self.assertIs(mock_pub, pub.Pub)
        self.assertIs(mock_insert_pub, self.client._handle_pub)
        self.assertIs(mock_feature_cvterm_pub, sequence.FeatureCvTermPub)
        self.assertIs(mock_insert_feature_cvterm_pub, self.client._handle_feature_cvterm_pub)

        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=1, cvterm_id=2, pub_id=3, feature_cvterm_id=4)
        mock_insert_pub.return_value = utils.EmptyObject(pub_id=33, uniquename="")
        mock_extract.return_value = []

        all_publications = self.client._handle_publications(self.default_gaf_record, feature_cvterm_entry,
                                                            feature_entry)
        mock_query.assert_called_with(sequence.FeatureCvTermPub, feature_cvterm_id=4)
        mock_pub.assert_not_called()
        self.assertEqual(len(all_publications), 0)

        mock_extract.return_value = ["new_publication"]
        all_publications = self.client._handle_publications(self.default_gaf_record, feature_cvterm_entry,
                                                            feature_entry)
        mock_pub.assert_called_with(uniquename="new_publication", type_id=71)
        self.assertEqual(mock_insert_pub.call_count, 1)
        mock_feature_cvterm_pub.assert_called_with(feature_cvterm_id=4, pub_id=33)
        self.assertEqual(mock_insert_feature_cvterm_pub.call_count, 1)
        self.assertEqual(len(all_publications), 1)

    def test_extract_cross_references(self):
        # Tests the function that extracts database cross references from a GAF record
        gaf_record = {"DB:Reference": ["somedb:someaccession", "PMID:12345", "another_publication"],
                      "With": ["evidencedb:evidenceaccession"]}
        crossrefs = self.client._extract_cross_references(gaf_record)
        self.assertEqual(crossrefs, ["evidencedb:evidenceaccession", "somedb:someaccession"])

    def test_extract_primary_publication(self):
        # Tests the function that extracts the primary publication from a GAF record
        gaf_record = {"DB:Reference": ["somedb:someaccession", "PMID:12345", "another_publication", "GO_REF:0001"]}
        primary_publication = self.client._extract_primary_publication(gaf_record)
        self.assertEqual(primary_publication, "PMID:12345")
        gaf_record = {"DB:Reference": ["somedb:someaccession", "another_publication", "GO_REF:0001"]}
        primary_publication = self.client._extract_primary_publication(gaf_record)
        self.assertEqual(primary_publication, "another_publication")
        gaf_record = {"DB:Reference": ["somedb:someaccession", "GO_REF:0001"]}
        primary_publication = self.client._extract_primary_publication(gaf_record)
        self.assertIsNone(primary_publication)

    def test_extract_secondary_publications(self):
        # Tests the function that extracts secondary publications from a GAF record
        gaf_record = {"DB:Reference": ["somedb:someaccession", "PMID:12345", "another_publication", "GO_REF:0001"]}
        secondary_publications = self.client._extract_secondary_publications(gaf_record)
        self.assertEqual(secondary_publications, ["another_publication"])
        gaf_record = {"DB:Reference": ["somedb:someaccession", "another_publication", "GO_REF:0001"]}
        secondary_publications = self.client._extract_secondary_publications(gaf_record)
        self.assertEqual(secondary_publications, [])


class TestGAFExport(unittest.TestCase):
    """Tests various functions used to export a GFF file from a database"""

    @classmethod
    def setUpClass(cls):
        # Creates an instance of the base class to be tested and instantiates global attributes
        cls.client = gaf.GAFExportClient("testuri", test_environment=True)
        cls.client._taxon_term = cv.CvTerm(cv_id=22, dbxref_id=93, name="taxonId", cvterm_id=93)
        cls.client._go_db = general.Db(name="GO", db_id=44)
        cls.client._product_db = general.Db(name="PRODUCT", db_id=55)

    @unittest.mock.patch("pychado.io.gaf.GAFExportClient.query_first")
    def test_extract_taxon_id(self, mock_query: unittest.mock.Mock):
        # Tests the function that extracts a taxon ID by a database query
        self.assertIs(mock_query, self.client.query_first)
        organism_entry = organism.Organism(genus="", species="", abbreviation="testorganism", organism_id=1)

        mock_query.return_value = None
        taxon = self.client._extract_taxon_id(organism_entry)
        mock_query.assert_called_with(organism.OrganismProp, organism_id=1, type_id=93)
        self.assertEqual(taxon, "taxon:testorganism")

        mock_query.return_value = organism.OrganismProp(organism_id=1, type_id=93, value="12345")
        taxon = self.client._extract_taxon_id(organism_entry)
        self.assertEqual(taxon, "taxon:12345")

    def test_write_gaf(self):
        # Tests the functions writing header and records to a GAF file
        gaf_file = tempfile.mkstemp()[1]
        gaf_file_handle = utils.open_file_write(gaf_file)
        gaf_record = {"k1": "v1", "k2": ["v2.1", "v2.2"]}
        self.client._write_gaf_header(gaf_file_handle)
        self.client._print_gaf_record(gaf_file_handle, gaf_record)
        utils.close(gaf_file_handle)
        actual_gaf_file = os.path.join(data_dir, 'gaf_records.gaf')
        self.assertTrue(filecmp.cmp(gaf_file, actual_gaf_file))
        os.remove(gaf_file)

    def test_stringify_gaf_attribute(self):
        # Tests the function that converts a list into a pipe-separated string
        string = self.client._stringify_gaf_attribute("bbb")
        self.assertEqual(string, "bbb")
        string = self.client._stringify_gaf_attribute(["a", "bbb"])
        self.assertEqual(string, "a|bbb")

    @unittest.mock.patch("pychado.io.gaf.GAFExportClient.query_feature_cvterm_ontology_terms")
    def test_extract_feature_cvterm_ontology_term(self, mock_query: unittest.mock.Mock):
        # Tests the function that extracts the ontology term associated with a feature_cvterm by a database query
        self.assertIs(mock_query, self.client.query_feature_cvterm_ontology_terms)
        feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=12, cvterm_id=33, pub_id=44, feature_cvterm_id=77)
        mock_query.return_value.configure_mock(**{"first.return_value": ("somedb", "someaccession")})
        ontology_term = self.client._extract_feature_cvterm_ontology_term(feature_cvterm_entry)
        mock_query.assert_called_with(77, 44)
        self.assertEqual(ontology_term, "somedb:someaccession")

    @unittest.mock.patch("pychado.io.gaf.GAFExportClient.query_feature_cvterm_properties")
    def test_extract_feature_cvterm_properties(self, mock_query: unittest.mock.Mock):
        # Tests the function that extracts the properties associated with a feature_cvterm by a database query
        self.assertIs(mock_query, self.client.query_feature_cvterm_properties)
        feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=12, cvterm_id=33, pub_id=44, feature_cvterm_id=77)
        mock_query.return_value.configure_mock(**{"all.return_value": [("k1", "v1"), ("k2", "v2")]})
        properties = self.client._extract_feature_cvterm_properties(feature_cvterm_entry)
        mock_query.assert_called_with(77)
        self.assertEqual(properties, {"k1": "v1", "k2": "v2"})

    @unittest.mock.patch("pychado.io.gaf.GAFExportClient.query_feature_cvterm_dbxrefs")
    def test_extract_feature_cvterm_dbxrefs(self, mock_query: unittest.mock.Mock):
        # Tests the function that extracts the cross references associated with a feature_cvterm by a database query
        self.assertIs(mock_query, self.client.query_feature_cvterm_dbxrefs)
        feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=12, cvterm_id=33, pub_id=44, feature_cvterm_id=77)
        mock_query.return_value.configure_mock(**{"all.return_value": [("somedb", "someacc"), ("otherdb", "otheracc")]})
        dbxrefs = self.client._extract_feature_cvterm_dbxrefs(feature_cvterm_entry)
        mock_query.assert_called_with(77)
        self.assertEqual(dbxrefs, ["somedb:someacc", "otherdb:otheracc"])

    @unittest.mock.patch("pychado.io.gaf.GAFExportClient.query_feature_cvterm_secondary_pubs")
    @unittest.mock.patch("pychado.io.gaf.GAFExportClient.query_feature_cvterm_pubs")
    def test_extract_feature_cvterm_publications(self, mock_query_primary: unittest.mock.Mock,
                                                 mock_query_secondary: unittest.mock.Mock):
        # Tests the function that extracts the publications associated with a feature_cvterm by a database query
        self.assertIs(mock_query_primary, self.client.query_feature_cvterm_pubs)
        self.assertIs(mock_query_secondary, self.client.query_feature_cvterm_secondary_pubs)
        feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=12, cvterm_id=33, pub_id=44, feature_cvterm_id=77)
        mock_query_primary.return_value.configure_mock(**{"all.return_value": [("pub0",)]})
        mock_query_secondary.return_value.configure_mock(**{"all.return_value": [("pub1",), ("pub2",)]})
        publications = self.client._extract_feature_cvterm_publications(feature_cvterm_entry)
        mock_query_primary.assert_called_with(77)
        mock_query_secondary.assert_called_with(77)
        self.assertEqual(publications, ["pub0", "pub1", "pub2"])

    @unittest.mock.patch("pychado.io.gaf.GAFExportClient.query_cvterm_namespace")
    def test_extract_go_namespace(self, mock_query: unittest.mock.Mock):
        # Tests the function that extracts the namespace of a feature_cvterm by a database query
        self.assertIs(mock_query, self.client.query_cvterm_namespace)
        feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=12, cvterm_id=33, pub_id=44, feature_cvterm_id=77)
        mock_query.return_value.configure_mock(**{"scalar.return_value": "somecv"})
        namespace = self.client._extract_go_namespace(feature_cvterm_entry)
        mock_query.assert_called_with(33)
        self.assertEqual(namespace, "somecv")

    def test_extract_feature_name(self):
        # Tests the function that extracts the name of a feature
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        featurename = self.client._extract_feature_name(feature_entry)
        self.assertEqual(featurename, "testname")
        feature_entry.name = "user_friendly_name"
        featurename = self.client._extract_feature_name(feature_entry)
        self.assertEqual(featurename, "user_friendly_name")

    @unittest.mock.patch("pychado.io.gaf.GAFExportClient.query_feature_synonyms")
    def test_extract_feature_synonyms(self, mock_query: unittest.mock.Mock):
        # Tests the function that extracts the synonyms of a feature by a database query
        self.assertIs(mock_query, self.client.query_feature_synonyms)
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        mock_query.return_value.configure_mock(**{"all.return_value": [("synonym", "s1"), ("alias", "s2")]})
        synonyms = self.client._extract_feature_synonyms(feature_entry)
        mock_query.assert_called_with(12)
        self.assertEqual(synonyms, ["s1", "s2"])

    @unittest.mock.patch("pychado.io.gaf.GAFExportClient.query_first")
    @unittest.mock.patch("pychado.io.gaf.GAFExportClient.query_feature_cvterm_by_ontology")
    def test_extract_product_name(self, mock_query: unittest.mock.Mock, mock_query_first: unittest.mock.Mock):
        # Tests the function that extracts the name of a gene product by a database query
        self.assertIs(mock_query, self.client.query_feature_cvterm_by_ontology)
        self.assertIs(mock_query_first, self.client.query_first)
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        mock_query.return_value.configure_mock(**{"first.return_value": sequence.FeatureCvTerm(
            feature_id=12, cvterm_id=44, pub_id=0)})
        mock_query_first.return_value = cv.CvTerm(cv_id=1, dbxref_id=2, name="someproduct")
        product_name = self.client._extract_product_name(feature_entry)
        mock_query.assert_called_with(12, 55)
        mock_query_first.assert_called_with(cv.CvTerm, cvterm_id=44)
        self.assertEqual(product_name, "someproduct")

    def test_create_gaf_record(self):
        # Tests the function that creates a GAF record
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=12, cvterm_id=33, pub_id=44, is_not=True)
        gaf_record = self.client._create_gaf_record(feature_cvterm_entry, feature_entry, "testdb", "testtaxon")
        self.assertEqual(len(gaf_record), 15)
        self.assertIn("Evidence", gaf_record)
        self.assertEqual(gaf_record["DB"], "testdb")
        self.assertEqual(gaf_record["DB_Object_ID"], "testname")
        self.assertEqual(gaf_record["Taxon_ID"], "testtaxon")
        self.assertEqual(gaf_record["Qualifier"], "NOT")

    def test_add_gaf_go_id(self):
        # Tests the function that adds a GO term to a GAF record
        gaf_record = {"DB_Object_ID": "objid"}
        self.client._add_gaf_go_id(gaf_record, "GO:12345")
        self.assertEqual(gaf_record["GO_ID"], "GO:12345")
        with self.assertRaises(iobase.DatabaseError):
            self.client._add_gaf_go_id(gaf_record, "")

    def test_add_gaf_aspect(self):
        # Tests the function that adds a GO namespace (aspect) to a GAF record
        gaf_record = {"DB_Object_ID": "objid", "GO_ID": "GO:12345"}
        self.client._add_gaf_aspect(gaf_record, "molecular_function")
        self.assertEqual(gaf_record["Aspect"], "F")
        with self.assertRaises(iobase.DatabaseError):
            self.client._add_gaf_aspect(gaf_record, "inexistent_namespace")

    def test_add_gaf_annotation_date(self):
        # Tests the function that adds an annotation date to a GAF record
        gaf_record = {"DB_Object_ID": "objid", "GO_ID": "GO:12345"}
        self.client._add_gaf_annotation_date(gaf_record, {"date": "20180101"})
        self.assertEqual(gaf_record["Date"], "20180101")
        self.client._add_gaf_annotation_date(gaf_record, {})
        self.assertEqual(gaf_record["Date"], utils.current_date())

    def test_add_gaf_evidence_code(self):
        # Tests the function that adds a GO evidence code to a GAF record
        gaf_record = {"DB_Object_ID": "objid", "GO_ID": "GO:12345"}
        self.client._add_gaf_evidence_code(gaf_record, {"evidence": "Inferred from High Throughput Experiment"})
        self.assertEqual(gaf_record["Evidence"], "HTP")
        self.client._add_gaf_evidence_code(gaf_record, {"evidence": "inexistent_evidence_code"})
        self.assertEqual(gaf_record["Evidence"], "NR")
        self.client._add_gaf_evidence_code(gaf_record, {})
        self.assertEqual(gaf_record["Evidence"], "NR")

    def test_add_gaf_assigning_database(self):
        # Tests the function that adds the assigned_by info to a GAF record
        gaf_record = {"DB": "testdb", "DB_Object_ID": "objid", "GO_ID": "GO:12345"}
        self.client._add_gaf_assigning_db(gaf_record, {})
        self.assertEqual(gaf_record["Assigned_By"], "testdb")
        self.client._add_gaf_assigning_db(gaf_record, {"assigned_by": "assigning_db"})
        self.assertEqual(gaf_record["Assigned_By"], "assigning_db")

    def test_add_gaf_withfrom_info(self):
        # Tests the functions that adds references for a GO evidence code to a GAF record
        gaf_record = {"DB_Object_ID": "objid"}
        self.client._add_gaf_withfrom_info(gaf_record, ["testdb:testaccession", "GO_REF:go_accession"])
        self.assertEqual(gaf_record["With"], ["testdb:testaccession"])

    def test_add_gaf_db_reference(self):
        # Tests the functions that adds database references to a GAF record
        gaf_record = {"DB_Object_ID": "objid"}
        self.client._add_gaf_db_references(gaf_record, ["PMID:12345", "null"],
                                           ["testdb:testaccession", "GO_REF:go_accession"])
        self.assertEqual(gaf_record["DB:Reference"], ["PMID:12345", "GO_REF:go_accession"])
        gaf_record.clear()
        self.client._add_gaf_db_references(gaf_record, [], [])
        self.assertEqual(gaf_record["DB:Reference"], ["GO_REF:0000002"])

    def test_add_gaf_object_type(self):
        # Tests the function that adds the feature type to a GAF record
        gaf_record = {"DB_Object_ID": "objid"}
        self.client._add_gaf_object_type(gaf_record, "testtype")
        self.assertEqual(gaf_record["DB_Object_Type"], "testtype")

    def test_add_gaf_object_name(self):
        # Tests the function that adds the name of the gene product to a GAF record
        gaf_record = {"DB_Object_ID": "objid"}
        self.client._add_gaf_object_name(gaf_record, "testproduct")
        self.assertEqual(gaf_record["DB_Object_Name"], "testproduct")

    def test_add_gaf_object_symbol(self):
        # Tests the function that adds the gene name to a GAF record
        gaf_record = {"DB_Object_ID": "objid"}
        self.client._add_gaf_object_symbol(gaf_record, "testname")
        self.assertEqual(gaf_record["DB_Object_Symbol"], "testname")
        with self.assertRaises(iobase.DatabaseError):
            self.client._add_gaf_object_symbol(gaf_record, "")

    def test_add_gaf_synonyms(self):
        # Tests the function that adds gene synonyms to a GAF record
        gaf_record = {"DB_Object_ID": "objid"}
        self.client._add_gaf_synonyms(gaf_record, ["s1", "s2"])
        self.assertEqual(gaf_record["Synonym"], ["s1", "s2"])


class TestGAFFunctions(unittest.TestCase):
    """Tests various general functions used in connection with GAF import/export"""

    @classmethod
    def setUpClass(cls):
        # Creates an instance of the base class to be tested
        cls.client = gaf.GAFClient("testuri", test_environment=True)
        cls.client._part_of_term = cv.CvTerm(cv_id=11, dbxref_id=91, name="part_of", is_relationshiptype=1,
                                             cvterm_id=91)
        cls.client._derives_from_term = cv.CvTerm(cv_id=11, dbxref_id=92, name="derives_from",
                                                  is_relationshiptype=1, cvterm_id=92)

    @unittest.mock.patch("pychado.io.gaf.GAFClient.query_first")
    def test_extract_feature_type(self, mock_query: unittest.mock.Mock):
        # Tests the function that extracts the type of a feature by a database query
        self.assertIs(mock_query, self.client.query_first)
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        mock_query.return_value = cv.CvTerm(cv_id=1, dbxref_id=2, name="sometype")
        featuretype = self.client._extract_feature_type(feature_entry)
        mock_query.assert_called_with(cv.CvTerm, cvterm_id=200)
        self.assertEqual(featuretype, "sometype")

    @unittest.mock.patch("pychado.io.gaf.GAFClient._extract_feature_type")
    def test_is_featuretype_valid(self, mock_extract: unittest.mock.Mock):
        # Tests the function that checks whether the type of a feature is valid
        self.assertIs(mock_extract, self.client._extract_feature_type)
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        mock_extract.return_value = "mRNA"
        self.assertTrue(self.client._is_featuretype_valid(feature_entry))
        mock_extract.return_value = "chromosome"
        self.assertFalse(self.client._is_featuretype_valid(feature_entry))

    @unittest.mock.patch("pychado.io.gaf.GAFClient._extract_polypeptide_of_feature")
    @unittest.mock.patch("pychado.io.gaf.GAFClient._extract_transcript_of_feature")
    @unittest.mock.patch("pychado.io.gaf.GAFClient._extract_gene_of_feature")
    def test_extract_requested_feature(self, mock_gene: unittest.mock.Mock, mock_transcript: unittest.mock.Mock,
                                       mock_polypeptide: unittest.mock.Mock):
        # Tests the function that extracts a feature of a requested type from the database
        self.assertIs(mock_gene, self.client._extract_gene_of_feature)
        self.assertIs(mock_transcript, self.client._extract_transcript_of_feature)
        self.assertIs(mock_polypeptide, self.client._extract_polypeptide_of_feature)
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)

        self.client._extract_requested_feature(feature_entry, "gene")
        mock_gene.assert_called_with(feature_entry)
        mock_transcript.assert_not_called()
        mock_polypeptide.assert_not_called()

        mock_gene.reset_mock()
        self.client._extract_requested_feature(feature_entry, "transcript")
        mock_gene.assert_not_called()
        mock_transcript.assert_called_with(feature_entry)
        mock_polypeptide.assert_not_called()

        mock_transcript.reset_mock()
        self.client._extract_requested_feature(feature_entry, "protein")
        mock_gene.assert_not_called()
        mock_transcript.assert_not_called()
        mock_polypeptide.assert_called_with(feature_entry)

        mock_polypeptide.reset_mock()
        requested_feature = self.client._extract_requested_feature(feature_entry, "default")
        mock_gene.assert_not_called()
        mock_transcript.assert_not_called()
        mock_polypeptide.assert_not_called()
        self.assertIs(requested_feature, feature_entry)

    @unittest.mock.patch("pychado.io.gaf.GAFClient.query_parent_features")
    @unittest.mock.patch("pychado.io.gaf.GAFClient._extract_feature_type")
    def test_extract_gene_of_feature(self, mock_type: unittest.mock.Mock, mock_parent: unittest.mock.Mock):
        # Tests the function that extracts the gene associated with a feature from the database
        self.assertIs(mock_type, self.client._extract_feature_type)
        self.assertIs(mock_parent, self.client.query_parent_features)
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        other_feature_entry = sequence.Feature(organism_id=11, type_id=300, uniquename="othername", feature_id=13)

        # Feature is a gene - return input
        mock_type.return_value = "gene"
        gene_entry = self.client._extract_gene_of_feature(feature_entry)
        mock_type.assert_called_with(feature_entry)
        mock_parent.assert_not_called()
        self.assertIs(gene_entry, feature_entry)

        # Feature is a transcript - return parent
        mock_type.return_value = "tRNA"
        mock_parent.reset_mock()
        mock_parent.return_value.configure_mock(**{"first.return_value": other_feature_entry})
        gene_entry = self.client._extract_gene_of_feature(feature_entry)
        mock_parent.assert_called_with(12, [91])
        self.assertIs(gene_entry, other_feature_entry)

        # Feature is a polypeptide - return grandparent
        mock_type.return_value = "polypeptide"
        mock_parent.reset_mock()
        gene_entry = self.client._extract_gene_of_feature(feature_entry)
        mock_parent.assert_called_with(13, [91])
        self.assertIn(unittest.mock.call(12, [92]), mock_parent.mock_calls)
        self.assertIs(gene_entry, other_feature_entry)

        # Feature is something else - return None
        mock_type.return_value = "chromosome"
        mock_parent.reset_mock()
        gene_entry = self.client._extract_gene_of_feature(feature_entry)
        mock_parent.assert_not_called()
        self.assertIsNone(gene_entry)

    @unittest.mock.patch("pychado.io.gaf.GAFClient.query_child_features")
    @unittest.mock.patch("pychado.io.gaf.GAFClient.query_parent_features")
    @unittest.mock.patch("pychado.io.gaf.GAFClient._extract_feature_type")
    def test_extract_transcript_of_feature(self, mock_type: unittest.mock.Mock, mock_parent: unittest.mock.Mock,
                                           mock_child: unittest.mock.Mock):
        # Tests the function that extracts the transcript associated with a feature from the database
        self.assertIs(mock_type, self.client._extract_feature_type)
        self.assertIs(mock_parent, self.client.query_parent_features)
        self.assertIs(mock_child, self.client.query_child_features)
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        other_feature_entry = sequence.Feature(organism_id=11, type_id=300, uniquename="othername", feature_id=13)

        # Feature is a transcript - return input
        mock_type.return_value = "tRNA"
        transcript_entry = self.client._extract_transcript_of_feature(feature_entry)
        mock_type.assert_called_with(feature_entry)
        mock_parent.assert_not_called()
        mock_child.assert_not_called()
        self.assertIs(transcript_entry, feature_entry)

        # Feature is a polypeptide - return parent
        mock_type.return_value = "polypeptide"
        mock_parent.reset_mock()
        mock_child.reset_mock()
        mock_parent.return_value.configure_mock(**{"first.return_value": other_feature_entry})
        transcript_entry = self.client._extract_transcript_of_feature(feature_entry)
        mock_parent.assert_called_with(12, [92])
        mock_child.assert_not_called()
        self.assertIs(transcript_entry, other_feature_entry)

        # Feature is a gene - return child
        mock_type.return_value = "gene"
        mock_parent.reset_mock()
        mock_child.reset_mock()
        mock_child.return_value.configure_mock(**{"first.return_value": other_feature_entry})
        transcript_entry = self.client._extract_transcript_of_feature(feature_entry)
        mock_parent.assert_not_called()
        mock_child.assert_called_with(12, 91)
        self.assertIs(transcript_entry, other_feature_entry)

        # Feature is something else - return None
        mock_type.return_value = "chromosome"
        mock_parent.reset_mock()
        mock_child.reset_mock()
        transcript_entry = self.client._extract_transcript_of_feature(feature_entry)
        mock_parent.assert_not_called()
        mock_child.assert_not_called()
        self.assertIsNone(transcript_entry)

    @unittest.mock.patch("pychado.io.gaf.GAFClient.query_child_features")
    @unittest.mock.patch("pychado.io.gaf.GAFClient._extract_feature_type")
    def test_extract_polypeptide_of_feature(self, mock_type: unittest.mock.Mock, mock_child: unittest.mock.Mock):
        # Tests the function that extracts the polypeptide associated with a feature from the database
        self.assertIs(mock_type, self.client._extract_feature_type)
        self.assertIs(mock_child, self.client.query_child_features)
        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        other_feature_entry = sequence.Feature(organism_id=11, type_id=300, uniquename="othername", feature_id=13)

        # Feature is a polypeptide - return input
        mock_type.return_value = "polypeptide"
        protein_entry = self.client._extract_polypeptide_of_feature(feature_entry)
        mock_type.assert_called_with(feature_entry)
        mock_child.assert_not_called()
        self.assertIs(protein_entry, feature_entry)

        # Feature is a transcript - return child
        mock_type.return_value = "tRNA"
        mock_child.reset_mock()
        mock_child.return_value.configure_mock(**{"first.return_value": other_feature_entry})
        protein_entry = self.client._extract_polypeptide_of_feature(feature_entry)
        mock_child.assert_called_with(12, 92)
        self.assertIs(protein_entry, other_feature_entry)

        # Feature is a gene - return grandchild
        mock_type.return_value = "gene"
        mock_child.reset_mock()
        protein_entry = self.client._extract_polypeptide_of_feature(feature_entry)
        mock_child.assert_called_with(13, 92)
        self.assertIn(unittest.mock.call(12, 91), mock_child.mock_calls)
        self.assertIs(protein_entry, other_feature_entry)

        # Feature is something else - return None
        mock_type.return_value = "chromosome"
        mock_child.reset_mock()
        protein_entry = self.client._extract_polypeptide_of_feature(feature_entry)
        mock_child.assert_not_called()
        self.assertIsNone(protein_entry)

    def test_convert_evidence_code(self):
        # Tests the function converting a GO evidence code abbreviation into the spelled-out form
        code = self.client._convert_evidence_code("HTP")
        self.assertEqual(code, "Inferred from High Throughput Experiment")
        code = self.client._convert_evidence_code("XYZ")
        self.assertEqual(code, "")

    def test_back_convert_evidence_code(self):
        # Tests the function converting a GO evidence code into its abbreviation
        code = self.client._back_convert_evidence_code("Inferred from High Throughput Experiment")
        self.assertEqual(code, "HTP")
        code = self.client._back_convert_evidence_code("tas")
        self.assertEqual(code, "TAS")
        code = self.client._back_convert_evidence_code("non_existent evidence code")
        self.assertEqual(code, "")

    def test_convert_namespace(self):
        # Tests the function converting a GO namespace into its abbreviation
        abbrev = self.client._convert_namespace("molecular_function")
        self.assertEqual(abbrev, "F")
        abbrev = self.client._convert_namespace("non_existent namespace")
        self.assertEqual(abbrev, "")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
