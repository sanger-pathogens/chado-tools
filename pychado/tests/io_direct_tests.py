import unittest.mock
from .. import utils
from ..io import direct
from ..orm import general, organism


class TestDirectIO(unittest.TestCase):
    """Tests various functions used to insert, update or delete entries in database tables"""

    @classmethod
    def setUpClass(cls):
        # Creates an instance of the base class to be tested and instantiates global attributes
        cls.client = direct.DirectIOClient("testuri", test_environment=True)

    @unittest.mock.patch("pychado.io.direct.DirectIOClient._handle_organism")
    @unittest.mock.patch("pychado.orm.organism.Organism")
    def test_handle_actual_organism(self, mock_organism: unittest.mock.Mock, mock_insert: unittest.mock.Mock):
        # Tests the function inserting data into the 'organism' table
        self.assertIs(mock_organism, organism.Organism)
        self.assertIs(mock_insert, self.client._handle_organism)

        org = self.client._handle_actual_organism("testgenus", "testspecies", "teststrain", "testabbreviation", "", "")
        mock_organism.assert_called_with(genus="testgenus", species="testspecies", infraspecific_name="teststrain",
                                         abbreviation="testabbreviation", common_name="testabbreviation", comment="")
        mock_insert.assert_called()
        self.assertIsNotNone(org)

    @unittest.mock.patch("pychado.io.direct.DirectIOClient._handle_organismprop")
    @unittest.mock.patch("pychado.orm.organism.OrganismProp")
    @unittest.mock.patch("pychado.io.direct.DirectIOClient._load_cvterm")
    def test_handle_organism_properties(self, mock_load_cvterm: unittest.mock.Mock,
                                        mock_organismprop: unittest.mock.Mock, mock_insert: unittest.mock.Mock):
        # Tests the function inserting data into the 'organismprop' table
        self.assertIs(mock_load_cvterm, self.client._load_cvterm)
        self.assertIs(mock_organismprop, organism.OrganismProp)
        self.assertIs(mock_insert, self.client._handle_organismprop)

        mock_load_cvterm.return_value = utils.EmptyObject(cvterm_id=33, name="")
        organism_entry = organism.Organism(genus="testgenus", species="testspecies", infraspecific_name="teststrain",
                                           abbreviation="testabbreviation", organism_id=1)

        props = self.client._handle_organism_properties(organism_entry, "", "")
        mock_load_cvterm.assert_not_called()
        mock_insert.assert_not_called()
        self.assertEqual(len(props), 0)

        props = self.client._handle_organism_properties(organism_entry, "v2", "12345")
        mock_load_cvterm.assert_any_call("version")
        mock_load_cvterm.assert_any_call("taxonId")
        mock_organismprop.assert_any_call(organism_id=1, type_id=33, value="v2")
        mock_organismprop.assert_any_call(organism_id=1, type_id=33, value="12345")
        mock_insert.assert_called()
        self.assertEqual(len(props), 2)

    @unittest.mock.patch("pychado.io.direct.DirectIOClient._handle_organism_dbxref")
    @unittest.mock.patch("pychado.orm.organism.OrganismDbxRef")
    @unittest.mock.patch("pychado.io.direct.DirectIOClient._handle_dbxref")
    @unittest.mock.patch("pychado.orm.general.DbxRef")
    @unittest.mock.patch("pychado.io.direct.DirectIOClient._load_db")
    def test_handle_organism_cross_references(self, mock_load_db: unittest.mock.Mock, mock_dbxref: unittest.mock.Mock,
                                              mock_insert_dbxref: unittest.mock.Mock,
                                              mock_organism_dbxref: unittest.mock.Mock,
                                              mock_insert_organism_dbxref: unittest.mock.Mock):
        # Tests the function inserting data into the 'organism_dbxref' table
        self.assertIs(mock_load_db, self.client._load_db)
        self.assertIs(mock_dbxref, general.DbxRef)
        self.assertIs(mock_insert_dbxref, self.client._handle_dbxref)
        self.assertIs(mock_organism_dbxref, organism.OrganismDbxRef)
        self.assertIs(mock_insert_organism_dbxref, self.client._handle_organism_dbxref)

        mock_load_db.return_value = utils.EmptyObject(db_id=5, name="WD")
        mock_insert_dbxref.return_value = utils.EmptyObject(dbxref_id=88)
        organism_entry = organism.Organism(genus="testgenus", species="testspecies", infraspecific_name="teststrain",
                                           abbreviation="testabbreviation", organism_id=1)

        xrefs = self.client._handle_organism_cross_references(organism_entry, "")
        mock_load_db.assert_not_called()
        mock_insert_dbxref.assert_not_called()
        mock_insert_organism_dbxref.assert_not_called()
        self.assertEqual(len(xrefs), 0)

        xrefs = self.client._handle_organism_cross_references(organism_entry, "Q9876")
        mock_load_db.assert_called_with("Wikidata")
        mock_dbxref.assert_called_with(db_id=5, accession="Q9876")
        mock_insert_dbxref.assert_called()
        mock_organism_dbxref.assert_called_with(organism_id=1, dbxref_id=88)
        mock_insert_organism_dbxref.assert_called()
        self.assertEqual(len(xrefs), 1)
