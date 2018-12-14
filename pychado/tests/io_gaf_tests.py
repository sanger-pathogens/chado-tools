import unittest.mock
from .. import dbutils, utils
from ..io import gaf
from ..orm import general, cv, pub, organism, sequence


class TestGAF(unittest.TestCase):
    """Tests various functions used to load a GFF file into a database"""

    connection_parameters = utils.parse_yaml(dbutils.default_configuration_file())
    connection_uri = dbutils.random_database_uri(connection_parameters)

    @classmethod
    def setUpClass(cls):
        # Creates an instance of the base class to be tested and instantiates global attributes
        cls.client = gaf.GAFImportClient(cls.connection_uri, test_environment=True)
        cls.client._date_term = cv.CvTerm(cv_id=11, dbxref_id=91, name="date", cvterm_id=91)
        cls.client._evidence_term = cv.CvTerm(cv_id=11, dbxref_id=92, name="evidence", cvterm_id=92)
        cls.client._default_pub = pub.Pub(uniquename="null", type_id=71, pub_id=33)
        cls.client._go_db = general.Db(name="GO", db_id=44)

    def setUp(self):
        # Creates a default GAF record
        self.default_gaf_record = {'DB': 'testdb', 'DB_Object_ID': 'testname', 'DB_Object_Symbol': 'testsymbol',
                                   'Qualifier': [''], 'GO_ID': 'GO:12345', 'DB:Reference': ['testdb:testaccession'],
                                   'Evidence': 'XYZ', 'With': ['evidencedb:evidenceaccession'], 'Aspect': 'C',
                                   'DB_Object_Name': 'testproduct', 'Synonym': [''], 'DB_Object_Type': 'transcript',
                                   'Taxon_ID': ['testtaxon'], 'Date': 'testdate', 'Assigned_By': 'testdb'}

    @unittest.mock.patch("pychado.io.gaf.GAFImportClient.query_first")
    def test_load_feature(self, mock_query: unittest.mock.Mock):
        # Tests the function loading the entry from the 'feature' table that corresponds to a GAF record
        self.assertIs(mock_query, self.client.query_first)
        organism_entry = organism.Organism(genus="", species="", abbreviation="testorganism", organism_id=1)
        self.client._load_feature(self.default_gaf_record, organism_entry)
        mock_query.assert_called_with(sequence.Feature, organism_id=1, uniquename="testname")

    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_feature_cvterm")
    @unittest.mock.patch("pychado.orm.sequence.FeatureCvTerm")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_pub")
    @unittest.mock.patch("pychado.orm.pub.Pub")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient.query_first")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient.query_feature_cvterm_by_ontology")
    def test_handle_ontology_term(self, mock_query: unittest.mock.Mock, mock_query_first: unittest.mock.Mock,
                                  mock_pub: unittest.mock.Mock, mock_insert_pub: unittest.mock.Mock,
                                  mock_feature_cvterm: unittest.mock.Mock,
                                  mock_insert_feature_cvterm: unittest.mock.Mock):
        # Tests the function transferring data from a GAF record to the 'feature_cvterm' table
        self.assertIs(mock_query, self.client.query_feature_cvterm_by_ontology)
        self.assertIs(mock_query_first, self.client.query_first)
        self.assertIs(mock_pub, pub.Pub)
        self.assertIs(mock_insert_pub, self.client._handle_pub)
        self.assertIs(mock_feature_cvterm, sequence.FeatureCvTerm)
        self.assertIs(mock_insert_feature_cvterm, self.client._handle_feature_cvterm)

        feature_entry = sequence.Feature(organism_id=11, type_id=200, uniquename="testname", feature_id=12)
        mock_query_first.side_effect = [utils.EmptyObject(db_id=33),
                                        utils.EmptyObject(dbxref_id=44),
                                        utils.EmptyObject(cvterm_id=55, name="")]
        mock_insert_pub.return_value = utils.EmptyObject(pub_id=66)

        ontology_term = self.client._handle_ontology_term(self.default_gaf_record, feature_entry)
        mock_query_first.assert_any_call(general.DbxRef, db_id=33, accession="12345")
        mock_query_first.assert_any_call(cv.CvTerm, dbxref_id=44)
        self.assertEqual(mock_query_first.call_count, 3)
        mock_pub.assert_any_call(uniquename="testdb:testaccession", type_id=71)
        self.assertEqual(mock_insert_pub.call_count, 1)
        mock_query.assert_called_with(12, [33])
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
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient.query_feature_cvterm_by_ontology")
    def test_handle_product_term(self, mock_query: unittest.mock.Mock,
                                 mock_db: unittest.mock.Mock, mock_insert_db: unittest.mock.Mock,
                                 mock_dbxref: unittest.mock.Mock, mock_insert_dbxref: unittest.mock.Mock,
                                 mock_cv: unittest.mock.Mock, mock_insert_cv: unittest.mock.Mock,
                                 mock_cvterm: unittest.mock.Mock, mock_insert_cvterm: unittest.mock.Mock,
                                 mock_pub: unittest.mock.Mock, mock_insert_pub: unittest.mock.Mock,
                                 mock_feature_cvterm: unittest.mock.Mock,
                                 mock_insert_feature_cvterm: unittest.mock.Mock):
        # Tests the function transferring data from a GAF record to the 'feature_cvterm' table
        self.assertIs(mock_query, self.client.query_feature_cvterm_by_ontology)
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
        mock_pub.assert_called_with(uniquename="testdb:testaccession", type_id=71)
        mock_query.assert_called_with(12, [22])
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
        feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=1, cvterm_id=2, pub_id=3, feature_cvterm_id=4)

        all_properties = self.client._handle_properties(self.default_gaf_record, feature_cvterm_entry)
        mock_query.assert_called_with(sequence.FeatureCvTermProp, feature_cvterm_id=4)
        mock_prop.assert_any_call(feature_cvterm_id=4, type_id=91, value="testdate")
        mock_prop.assert_any_call(feature_cvterm_id=4, type_id=92, value="XYZ")
        self.assertEqual(mock_insert_prop.call_count, 2)
        self.assertEqual(len(all_properties), 2)

    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_feature_cvterm_dbxref")
    @unittest.mock.patch("pychado.orm.sequence.FeatureCvTermDbxRef")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_dbxref")
    @unittest.mock.patch("pychado.orm.general.DbxRef")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient._handle_db")
    @unittest.mock.patch("pychado.orm.general.Db")
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient.query_all")
    def test_handle_crossrefs(self, mock_query: unittest.mock.Mock, mock_db: unittest.mock.Mock,
                              mock_insert_db: unittest.mock.Mock, mock_dbxref: unittest.mock.Mock,
                              mock_insert_dbxref: unittest.mock.Mock, mock_feature_cvterm_dbxref: unittest.mock.Mock,
                              mock_insert_feature_cvterm_dbxref: unittest.mock.Mock):
        # Tests the function transferring data from a GAF record to the 'feature_cvterm_dbxref' table
        self.assertIs(mock_query, self.client.query_all)
        self.assertIs(mock_db, general.Db)
        self.assertIs(mock_insert_db, self.client._handle_db)
        self.assertIs(mock_dbxref, general.DbxRef)
        self.assertIs(mock_insert_dbxref, self.client._handle_dbxref)
        self.assertIs(mock_feature_cvterm_dbxref, sequence.FeatureCvTermDbxRef)
        self.assertIs(mock_insert_feature_cvterm_dbxref, self.client._handle_feature_cvterm_dbxref)

        feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=1, cvterm_id=2, pub_id=3, feature_cvterm_id=4)
        mock_insert_db.return_value = utils.EmptyObject(db_id=44, name="")
        mock_insert_dbxref.return_value = utils.EmptyObject(dbxref_id=55, accession="", version="")

        all_crossrefs = self.client._handle_crossrefs(self.default_gaf_record, feature_cvterm_entry)
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
    @unittest.mock.patch("pychado.io.gaf.GAFImportClient.query_all")
    def test_handle_publications(self, mock_query: unittest.mock.Mock,
                                 mock_pub: unittest.mock.Mock, mock_insert_pub: unittest.mock.Mock,
                                 mock_feature_cvterm_pub: unittest.mock.Mock,
                                 mock_insert_feature_cvterm_pub: unittest.mock.Mock):
        # Tests the function transferring data from a GAF record to the 'feature_cvterm_pub' table
        self.assertIs(mock_query, self.client.query_all)
        self.assertIs(mock_pub, pub.Pub)
        self.assertIs(mock_insert_pub, self.client._handle_pub)
        self.assertIs(mock_feature_cvterm_pub, sequence.FeatureCvTermPub)
        self.assertIs(mock_insert_feature_cvterm_pub, self.client._handle_feature_cvterm_pub)

        feature_cvterm_entry = sequence.FeatureCvTerm(feature_id=1, cvterm_id=2, pub_id=3, feature_cvterm_id=4)
        mock_insert_pub.return_value = utils.EmptyObject(pub_id=33, uniquename="")

        all_publications = self.client._handle_publications(self.default_gaf_record, feature_cvterm_entry)
        mock_query.assert_called_with(sequence.FeatureCvTermPub, feature_cvterm_id=4)
        mock_pub.assert_not_called()
        self.assertEqual(len(all_publications), 0)

        self.default_gaf_record["DB:Reference"].append("new_publication")
        all_publications = self.client._handle_publications(self.default_gaf_record, feature_cvterm_entry)
        mock_pub.assert_called_with(uniquename="new_publication", type_id=71)
        self.assertEqual(mock_insert_pub.call_count, 1)
        mock_feature_cvterm_pub.assert_called_with(feature_cvterm_id=4, pub_id=33)
        self.assertEqual(mock_insert_feature_cvterm_pub.call_count, 1)
        self.assertEqual(len(all_publications), 1)

    def test_convert_evidence_code(self):
        # Tests the function converting an evidence code abbreviation into the spelled-out form
        code = self.client._convert_evidence_code("HTP")
        self.assertEqual(code, "Inferred from High Throughput Experiment")
        code = self.client._convert_evidence_code("XYZ")
        self.assertEqual(code, "XYZ")


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
