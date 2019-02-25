import unittest
import sqlalchemy.exc
import sqlalchemy.schema
from .. import dbutils, utils
from ..io import iobase
from ..orm import base, general, cv, organism, pub, sequence, companalysis, audit


class TestPublic(unittest.TestCase):
    """Base class for testing the setup of all tables defined in the 'public' schema of the ORM"""

    connection_parameters = utils.parse_yaml(dbutils.default_configuration_file())
    connection_uri = dbutils.random_database_uri(connection_parameters)

    @classmethod
    def setUpClass(cls):
        # Creates a database, establishes a connection and creates tables
        dbutils.create_database(cls.connection_uri)
        cls.client = iobase.IOClient(cls.connection_uri)
        schema_base = base.PublicBase
        schema_metadata = schema_base.metadata
        schema_base.metadata.create_all(cls.client.engine, tables=schema_metadata.sorted_tables)

    @classmethod
    def tearDownClass(cls):
        # Drops the database
        dbutils.drop_database(cls.connection_uri, True)

    def tearDown(self):
        # Rolls back all changes to the database
        self.client.session.rollback()

    # Test suite for the Chado 'db' table
    def add_db_object(self) -> general.Db:
        # Insert a random entry into the 'db' table
        db_obj = general.Db(name=utils.random_string(10), description=utils.random_string(10),
                            urlprefix=utils.random_string(10), url=utils.random_string(10))
        self.client.add_and_flush(db_obj)
        return db_obj

    def test_db(self):
        # Test adding a new 'db' object to the database
        existing_obj = self.add_db_object()
        self.assertIsNotNone(existing_obj.db_id)
        self.assertEqual(existing_obj.__tablename__, 'db')

    def test_db_c1(self):
        # Test unique constraint on 'db.name'
        existing_obj = self.add_db_object()
        obj = general.Db(name=existing_obj.name)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'dbxref' table
    def add_dbxref_object(self) -> general.DbxRef:
        # Insert a random entry into the 'dbxref' table
        db_obj = self.add_db_object()
        dbxref_obj = general.DbxRef(db_id=db_obj.db_id, accession=utils.random_string(10),
                                    version=utils.random_string(10), description=utils.random_string(10))
        self.client.add_and_flush(dbxref_obj)
        return dbxref_obj

    def test_dbxref(self):
        # Test adding a new 'dbxref' object to the database
        existing_obj = self.add_dbxref_object()
        self.assertIsNotNone(existing_obj.dbxref_id)
        self.assertEqual(existing_obj.__tablename__, 'dbxref')

    def test_dbxref_db_id_fkey(self):
        # Test foreign key constraint on 'dbxref.db_id'
        existing_obj = self.add_dbxref_object()
        obj = general.DbxRef(db_id=(existing_obj.db_id+100), accession=utils.random_string(10))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_dbxref_c1(self):
        # Test unique constraint on 'dbxref.db_id', 'dbxref.accession', 'dbxref.version'
        existing_obj = self.add_dbxref_object()
        obj = general.DbxRef(db_id=existing_obj.db_id, accession=existing_obj.accession,
                             version=existing_obj.version)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'cv' table
    def add_cv_object(self) -> cv.Cv:
        # Insert a random entry into the 'cv' table
        cv_obj = cv.Cv(name=utils.random_string(10), definition=utils.random_string(10))
        self.client.add_and_flush(cv_obj)
        return cv_obj

    def test_cv(self):
        # Test adding a new 'cv' object to the database
        existing_obj = self.add_cv_object()
        self.assertIsNotNone(existing_obj.cv_id)
        self.assertEqual(existing_obj.__tablename__, 'cv')

    def test_cv_c1(self):
        # Test unique constraint on 'cv.name'
        existing_obj = self.add_cv_object()
        obj = cv.Cv(name=existing_obj.name)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'cvterm' table
    def add_cvterm_object(self) -> cv.CvTerm:
        # Insert a random entry into the 'cvterm' table
        cv_obj = self.add_cv_object()
        dbxref_obj = self.add_dbxref_object()
        cvterm_obj = cv.CvTerm(cv_id=cv_obj.cv_id, dbxref_id=dbxref_obj.dbxref_id, name=utils.random_string(10),
                               definition=utils.random_string(10), is_obsolete=0)
        self.client.add_and_flush(cvterm_obj)
        return cvterm_obj

    def test_cvterm(self):
        # Test adding a new 'cvterm' object to the database
        existing_obj = self.add_cvterm_object()
        self.assertIsNotNone(existing_obj.cvterm_id)
        self.assertEqual(existing_obj.__tablename__, 'cvterm')

    def test_cvterm_cv_id_fkey(self):
        # Test foreign key constraint on 'cvterm.cv_id'
        existing_obj = self.add_cvterm_object()
        obj = cv.CvTerm(cv_id=(existing_obj.cv_id+100), dbxref_id=existing_obj.dbxref_id, name=utils.random_string(10))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvterm_dbxref_id_fkey(self):
        # Test foreign key constraint on 'cvterm.dbxref_id'
        existing_obj = self.add_cvterm_object()
        obj = cv.CvTerm(cv_id=existing_obj.cv_id, dbxref_id=(existing_obj.dbxref_id+100), name=utils.random_string(10))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvterm_c1(self):
        # Test unique constraint on 'cvterm.dbxref_id'
        existing_obj = self.add_cvterm_object()
        obj = cv.CvTerm(cv_id=existing_obj.cv_id, dbxref_id=existing_obj.dbxref_id, name=utils.random_string(10))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvterm_c2(self):
        # Test unique constraint on 'cvterm.cv_id', 'cvterm.name', 'cvterm.is_obsolete'
        existing_obj = self.add_cvterm_object()
        dbxref_object = self.add_dbxref_object()
        obj = cv.CvTerm(cv_id=existing_obj.cv_id, dbxref_id=dbxref_object.dbxref_id, name=existing_obj.name,
                        is_obsolete=existing_obj.is_obsolete)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'cvtermprop' table
    def add_cvtermprop_object(self) -> cv.CvTermProp:
        # Insert a random entry into the 'cvtermprop' table
        cvterm_obj = self.add_cvterm_object()
        type_obj = self.add_cvterm_object()
        cvtermprop_obj = cv.CvTermProp(cvterm_id=cvterm_obj.cvterm_id, type_id=type_obj.cvterm_id,
                                       value=utils.random_string(10), rank=utils.random_integer(100))
        self.client.add_and_flush(cvtermprop_obj)
        return cvtermprop_obj

    def test_cvtermprop(self):
        # Test adding a new 'cvtermprop' object to the database
        existing_obj = self.add_cvtermprop_object()
        self.assertIsNotNone(existing_obj.cvtermprop_id)
        self.assertEqual(existing_obj.__tablename__, 'cvtermprop')

    def test_cvtermprop_cvterm_id_fkey(self):
        # Test foreign key constraint on 'cvtermprop.cvterm_id'
        existing_obj = self.add_cvtermprop_object()
        obj = cv.CvTermProp(cvterm_id=(existing_obj.cvterm_id+100), type_id=existing_obj.type_id,
                            value=utils.random_string(10), rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvtermprop_type_id_fkey(self):
        # Test foreign key constraint on 'cvtermprop.type_id'
        existing_obj = self.add_cvtermprop_object()
        obj = cv.CvTermProp(cvterm_id=existing_obj.cvterm_id, type_id=(existing_obj.type_id+100),
                            value=utils.random_string(10), rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvtermprop_c1(self):
        # Test unique constraint on 'cvtermprop.cvterm_id', 'cvtermprop.type_id', 'cvtermprop.value', 'cvtermprop.rank'
        existing_obj = self.add_cvtermprop_object()
        obj = cv.CvTermProp(cvterm_id=existing_obj.cvterm_id, type_id=existing_obj.type_id,
                            value=existing_obj.value, rank=existing_obj.rank)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'cvterm_relationship' table
    def add_cvterm_relationship_object(self) -> cv.CvTermRelationship:
        # Insert a random entry into the 'cvterm_relationship' table
        type_obj = self.add_cvterm_object()
        subject_obj = self.add_cvterm_object()
        object_obj = self.add_cvterm_object()
        cvterm_relationship_obj = cv.CvTermRelationship(type_id=type_obj.cvterm_id, subject_id=subject_obj.cvterm_id,
                                                        object_id=object_obj.cvterm_id)
        self.client.add_and_flush(cvterm_relationship_obj)
        return cvterm_relationship_obj

    def test_cvterm_relationship(self):
        # Test adding a new 'cvterm_relationship' object to the database
        existing_obj = self.add_cvterm_relationship_object()
        self.assertIsNotNone(existing_obj.cvterm_relationship_id)
        self.assertEqual(existing_obj.__tablename__, 'cvterm_relationship')

    def test_cvterm_relationship_type_id_fkey(self):
        # Test foreign key constraint on 'cvterm_relationship.type_id'
        existing_obj = self.add_cvterm_relationship_object()
        obj = cv.CvTermRelationship(type_id=(existing_obj.type_id+100), subject_id=existing_obj.subject_id,
                                    object_id=existing_obj.object_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvterm_relationship_subject_id_fkey(self):
        # Test foreign key constraint on 'cvterm_relationship.subject_id'
        existing_obj = self.add_cvterm_relationship_object()
        obj = cv.CvTermRelationship(type_id=existing_obj.type_id, subject_id=(existing_obj.subject_id+100),
                                    object_id=existing_obj.object_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvterm_relationship_object_id_fkey(self):
        # Test foreign key constraint on 'cvterm_relationship.object_id'
        existing_obj = self.add_cvterm_relationship_object()
        obj = cv.CvTermRelationship(type_id=existing_obj.type_id, subject_id=existing_obj.subject_id,
                                    object_id=(existing_obj.object_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvterm_relationship_c1(self):
        # Test unique constraint on 'cvterm_relationship.subject_id', 'cvterm_relationship.object_id',
        # 'cvterm_relationship.type_id'
        existing_obj = self.add_cvterm_relationship_object()
        obj = cv.CvTermRelationship(type_id=existing_obj.type_id, subject_id=existing_obj.subject_id,
                                    object_id=existing_obj.object_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'cvtermsynonym' table
    def add_cvtermsynonym_object(self) -> cv.CvTermSynonym:
        # Insert a random entry into the 'cvtermsynonym' table
        cvterm_obj = self.add_cvterm_object()
        type_obj = self.add_cvterm_object()
        cvtermsynonym_obj = cv.CvTermSynonym(cvterm_id=cvterm_obj.cvterm_id, synonym=utils.random_string(10),
                                             type_id=type_obj.cvterm_id)
        self.client.add_and_flush(cvtermsynonym_obj)
        return cvtermsynonym_obj

    def test_cvtermsynonym(self):
        # Test adding a new 'cvtermsynonym' object to the database
        existing_obj = self.add_cvtermsynonym_object()
        self.assertIsNotNone(existing_obj.cvtermsynonym_id)
        self.assertEqual(existing_obj.__tablename__, 'cvtermsynonym')

    def test_cvtermsynonym_cvterm_id_fkey(self):
        # Test foreign key constraint on 'cvtermsynonym.cvterm_id'
        existing_obj = self.add_cvtermsynonym_object()
        obj = cv.CvTermSynonym(cvterm_id=(existing_obj.cvterm_id+100), synonym=utils.random_string(10),
                               type_id=existing_obj.type_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvtermsynonym_type_id_fkey(self):
        # Test foreign key constraint on 'cvtermsynonym.type_id'
        existing_obj = self.add_cvtermsynonym_object()
        obj = cv.CvTermSynonym(cvterm_id=existing_obj.cvterm_id, synonym=utils.random_string(10),
                               type_id=(existing_obj.type_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvtermsynonym_c1(self):
        # Test unique constraint on 'cvtermsynonym.cvterm_id', 'cvtermsynonym.synonym'
        existing_obj = self.add_cvtermsynonym_object()
        obj = cv.CvTermSynonym(cvterm_id=existing_obj.cvterm_id, synonym=existing_obj.synonym)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'cvterm_dbxref' table
    def add_cvterm_dbxref_object(self) -> cv.CvTermDbxRef:
        # Insert a random entry into the 'cvterm_dbxref' table
        cvterm_obj = self.add_cvterm_object()
        dbxref_obj = self.add_dbxref_object()
        cvterm_dbxref_obj = cv.CvTermDbxRef(cvterm_id=cvterm_obj.cvterm_id, dbxref_id=dbxref_obj.dbxref_id,
                                            is_for_definition=0)
        self.client.add_and_flush(cvterm_dbxref_obj)
        return cvterm_dbxref_obj

    def test_cvterm_dbxref(self):
        # Test adding a new 'cvterm_dbxref' object to the database
        existing_obj = self.add_cvterm_dbxref_object()
        self.assertIsNotNone(existing_obj.cvterm_dbxref_id)
        self.assertEqual(existing_obj.__tablename__, 'cvterm_dbxref')

    def test_cvterm_dbxref_cvterm_id_fkey(self):
        # Test foreign key constraint on 'cvterm_dbxref.cvterm_id'
        existing_obj = self.add_cvterm_dbxref_object()
        obj = cv.CvTermDbxRef(cvterm_id=(existing_obj.cvterm_id+100), dbxref_id=existing_obj.dbxref_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvterm_dbxref_dbxref_id_fkey(self):
        # Test foreign key constraint on 'cvterm_dbxref.dbxref_id'
        existing_obj = self.add_cvterm_dbxref_object()
        obj = cv.CvTermDbxRef(cvterm_id=existing_obj.cvterm_id, dbxref_id=(existing_obj.dbxref_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvterm_dbxref_cq(self):
        # Test unique constraint on 'cvterm_dbxref.cvterm_id', 'cvterm_dbxref.dbxref_id'
        existing_obj = self.add_cvterm_dbxref_object()
        obj = cv.CvTermDbxRef(cvterm_id=existing_obj.cvterm_id, dbxref_id=existing_obj.dbxref_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'cvtermpath' table
    def add_cvtermpath_object(self) -> cv.CvTermPath:
        # Insert a random entry into the 'cvtermpath' table
        type_obj = self.add_cvterm_object()
        subject_obj = self.add_cvterm_object()
        object_obj = self.add_cvterm_object()
        cv_obj = self.add_cv_object()
        cvtermpath_obj = cv.CvTermPath(type_id=type_obj.cvterm_id, subject_id=subject_obj.cvterm_id,
                                       object_id=object_obj.cvterm_id, cv_id=cv_obj.cv_id, pathdistance=1)
        self.client.add_and_flush(cvtermpath_obj)
        return cvtermpath_obj

    def test_cvtermpath(self):
        # Test adding a new 'cvtermpath' object to the database
        existing_obj = self.add_cvtermpath_object()
        self.assertIsNotNone(existing_obj.cvtermpath_id)
        self.assertEqual(existing_obj.__tablename__, 'cvtermpath')

    def test_cvtermpath_type_id_fkey(self):
        # Test foreign key constraint on 'cvtermpath.type_id'
        existing_obj = self.add_cvtermpath_object()
        obj = cv.CvTermPath(type_id=(existing_obj.type_id+100), subject_id=existing_obj.subject_id,
                            object_id=existing_obj.object_id, cv_id=existing_obj.cv_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvtermpath_subject_id_fkey(self):
        # Test foreign key constraint on 'cvtermpath.subject_id'
        existing_obj = self.add_cvtermpath_object()
        obj = cv.CvTermPath(type_id=existing_obj.type_id, subject_id=(existing_obj.subject_id+100),
                            object_id=existing_obj.object_id, cv_id=existing_obj.cv_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvtermpath_object_id_fkey(self):
        # Test foreign key constraint on 'cvtermpath.object_id'
        existing_obj = self.add_cvtermpath_object()
        obj = cv.CvTermPath(type_id=existing_obj.type_id, subject_id=existing_obj.subject_id,
                            object_id=(existing_obj.object_id+100), cv_id=existing_obj.cv_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvtermpath_cv_id_fkey(self):
        # Test foreign key constraint on 'cvtermpath.cv_id'
        existing_obj = self.add_cvtermpath_object()
        obj = cv.CvTermPath(type_id=existing_obj.type_id, subject_id=existing_obj.subject_id,
                            object_id=existing_obj.object_id, cv_id=(existing_obj.cv_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_cvtermpath_c1(self):
        # Test unique constraint on 'cvtermpath.type_id', 'cvtermpath.subject_id', 'cvtermpath.object_id',
        # 'cvtermpath.pathdistance'
        existing_obj = self.add_cvtermpath_object()
        obj = cv.CvTermPath(type_id=existing_obj.type_id, subject_id=existing_obj.subject_id,
                            object_id=existing_obj.object_id, cv_id=existing_obj.cv_id,
                            pathdistance=existing_obj.pathdistance)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'dbxrefprop' table
    def add_dbxrefprop_object(self) -> cv.DbxRefProp:
        # Insert a random entry into the 'dbxrefprop' table
        dbxref_obj = self.add_dbxref_object()
        type_obj = self.add_cvterm_object()
        dbxrefprop_obj = cv.DbxRefProp(dbxref_id=dbxref_obj.dbxref_id, type_id=type_obj.cvterm_id,
                                       value=utils.random_string(10), rank=utils.random_integer(100))
        self.client.add_and_flush(dbxrefprop_obj)
        return dbxrefprop_obj

    def test_dbxrefprop(self):
        # Test adding a new 'dbxrefprop' object to the database
        existing_obj = self.add_dbxrefprop_object()
        self.assertIsNotNone(existing_obj.dbxrefprop_id)
        self.assertEqual(existing_obj.__tablename__, 'dbxrefprop')

    def test_dbxrefprop_dbxref_id_fkey(self):
        # Test foreign key constraint on 'dbxrefprop.dbxref_id'
        existing_obj = self.add_dbxrefprop_object()
        obj = cv.DbxRefProp(dbxref_id=(existing_obj.dbxref_id+100), type_id=existing_obj.type_id,
                            value=utils.random_string(10), rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_dbxrefprop_type_id_fkey(self):
        # Test foreign key constraint on 'dbxrefprop.type_id'
        existing_obj = self.add_dbxrefprop_object()
        obj = cv.DbxRefProp(dbxref_id=existing_obj.dbxref_id, type_id=(existing_obj.type_id+100),
                            value=utils.random_string(10), rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_dbxrefprop_c1(self):
        # Test unique constraint on 'dbxrefprop.dbxref_id', 'dbxrefprop.type_id', 'dbxrefprop.value', 'dbxrefprop.rank'
        existing_obj = self.add_dbxrefprop_object()
        obj = cv.DbxRefProp(dbxref_id=existing_obj.dbxref_id, type_id=existing_obj.type_id,
                            value=existing_obj.value, rank=existing_obj.rank)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'organism' table
    def add_organism_object(self) -> organism.Organism:
        # Insert a random entry into the 'organism' table
        type_obj = self.add_cvterm_object()
        organism_obj = organism.Organism(genus=utils.random_string(10), species=utils.random_string(10),
                                         abbreviation=utils.random_string(10), common_name=utils.random_string(10),
                                         infraspecific_name=utils.random_string(10), comment=utils.random_string(10),
                                         type_id=type_obj.cvterm_id)
        self.client.add_and_flush(organism_obj)
        return organism_obj

    def test_organism(self):
        # Test adding a new 'organism' object to the database
        existing_obj = self.add_organism_object()
        self.assertIsNotNone(existing_obj.organism_id)
        self.assertEqual(existing_obj.__tablename__, 'organism')

    def test_organism_type_id_fkey(self):
        # Test foreign key constraint on 'organism.type_id'
        existing_obj = self.add_organism_object()
        obj = organism.Organism(genus=utils.random_string(10), species=utils.random_string(10),
                                abbreviation=utils.random_string(10), type_id=(existing_obj.type_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_organism_c1(self):
        # Test unique constraint on 'organism.genus', 'organism.species', 'organism.infraspecific_name'
        existing_obj = self.add_organism_object()
        obj = organism.Organism(genus=existing_obj.genus, species=existing_obj.species,
                                infraspecific_name=existing_obj.infraspecific_name,
                                abbreviation=utils.random_string(10))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_organism_c2(self):
        # Test unique constraint on 'organism.abbreviation'
        existing_obj = self.add_organism_object()
        obj = organism.Organism(genus=utils.random_string(10), species=utils.random_string(10),
                                infraspecific_name=utils.random_string(10), abbreviation=existing_obj.abbreviation)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'organism_dbxref' table
    def add_organism_dbxref_object(self) -> organism.OrganismDbxRef:
        # Insert a random entry into the 'organism_dbxref' table
        organism_obj = self.add_organism_object()
        dbxref_obj = self.add_dbxref_object()
        organism_dbxref_obj = organism.OrganismDbxRef(organism_id=organism_obj.organism_id,
                                                      dbxref_id=dbxref_obj.dbxref_id)
        self.client.add_and_flush(organism_dbxref_obj)
        return organism_dbxref_obj

    def test_organism_dbxref(self):
        # Test adding a new 'organism_dbxref' object to the database
        existing_obj = self.add_organism_dbxref_object()
        self.assertIsNotNone(existing_obj.organism_dbxref_id)
        self.assertEqual(existing_obj.__tablename__, 'organism_dbxref')

    def test_organism_dbxref_organism_id_fkey(self):
        # Test foreign key constraint on 'organism_dbxref.organism_id'
        existing_obj = self.add_organism_dbxref_object()
        obj = organism.OrganismDbxRef(organism_id=(existing_obj.organism_id+100), dbxref_id=existing_obj.dbxref_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_organism_dbxref_dbxref_id_fkey(self):
        # Test foreign key constraint on 'organism_dbxref.dbxref_id'
        existing_obj = self.add_organism_dbxref_object()
        obj = organism.OrganismDbxRef(organism_id=existing_obj.organism_id, dbxref_id=(existing_obj.dbxref_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_organism_dbxref_c1(self):
        # Test unique constraint on 'organism_dbxref.organism_id', 'organism_dbxref.dbxref_id'
        existing_obj = self.add_organism_dbxref_object()
        obj = organism.OrganismDbxRef(organism_id=existing_obj.organism_id, dbxref_id=existing_obj.dbxref_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'organismprop' table
    def add_organismprop_object(self) -> organism.OrganismProp:
        # Insert a random entry into the 'organismprop' table
        organism_obj = self.add_organism_object()
        type_obj = self.add_cvterm_object()
        organismprop_obj = organism.OrganismProp(organism_id=organism_obj.organism_id, type_id=type_obj.cvterm_id,
                                                 value=utils.random_string(10), rank=utils.random_integer(100))
        self.client.add_and_flush(organismprop_obj)
        return organismprop_obj

    def test_organismprop(self):
        # Test adding a new 'organismprop' object to the database
        existing_obj = self.add_organismprop_object()
        self.assertIsNotNone(existing_obj.organismprop_id)
        self.assertEqual(existing_obj.__tablename__, 'organismprop')

    def test_organismprop_organism_id_fkey(self):
        # Test foreign key constraint on 'organismprop.organism_id'
        existing_obj = self.add_organismprop_object()
        obj = organism.OrganismProp(organism_id=(existing_obj.organism_id+100), type_id=existing_obj.type_id,
                                    value=utils.random_string(10), rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_organismprop_type_id_fkey(self):
        # Test foreign key constraint on 'organismprop.type_id'
        existing_obj = self.add_organismprop_object()
        obj = organism.OrganismProp(organism_id=existing_obj.organism_id, type_id=(existing_obj.type_id+100),
                                    value=utils.random_string(10), rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_organismprop_c1(self):
        # Test unique constraint on 'organismprop.organism_id', 'organismprop.type_id', 'organismprop.rank'
        existing_obj = self.add_organismprop_object()
        obj = organism.OrganismProp(organism_id=existing_obj.organism_id, type_id=existing_obj.type_id,
                                    rank=existing_obj.rank)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'pub' table
    def add_pub_object(self) -> pub.Pub:
        # Insert a random entry into the 'pub' table
        type_obj = self.add_cvterm_object()
        pub_obj = pub.Pub(uniquename=utils.random_string(10), type_id=type_obj.cvterm_id, title=utils.random_string(10),
                          volumetitle=utils.random_string(10), volume=utils.random_string(10),
                          series_name=utils.random_string(10), issue=utils.random_string(10),
                          pyear=utils.random_string(10), pages=utils.random_string(10), miniref=utils.random_string(10),
                          is_obsolete=False, publisher=utils.random_string(10), pubplace=utils.random_string(10))
        self.client.add_and_flush(pub_obj)
        return pub_obj

    def test_pub(self):
        # Test adding a new 'pub' object to the database
        existing_obj = self.add_pub_object()
        self.assertIsNotNone(existing_obj.pub_id)
        self.assertEqual(existing_obj.__tablename__, 'pub')

    def test_pub_type_id_fkey(self):
        # Test foreign key constraint on 'pub.type_id'
        existing_obj = self.add_pub_object()
        obj = pub.Pub(uniquename=utils.random_string(10), type_id=(existing_obj.type_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_pub_c1(self):
        # Test unique constraint on 'pub.uniquename'
        existing_obj = self.add_pub_object()
        obj = pub.Pub(uniquename=existing_obj.uniquename, type_id=existing_obj.type_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'pub_dbxref' table
    def add_pub_dbxref_object(self) -> pub.PubDbxRef:
        # Insert a random entry into the 'pub_dbxref' table
        pub_obj = self.add_pub_object()
        dbxref_obj = self.add_dbxref_object()
        pub_dbxref_obj = pub.PubDbxRef(pub_id=pub_obj.pub_id, dbxref_id=dbxref_obj.dbxref_id, is_current=True)
        self.client.add_and_flush(pub_dbxref_obj)
        return pub_dbxref_obj

    def test_pub_dbxref(self):
        # Test adding a new 'pub_dbxref' object to the database
        existing_obj = self.add_pub_dbxref_object()
        self.assertIsNotNone(existing_obj.pub_dbxref_id)
        self.assertEqual(existing_obj.__tablename__, 'pub_dbxref')

    def test_pub_dbxref_pub_id_fkey(self):
        # Test foreign key constraint on 'pub_dbxref.pub_id'
        existing_obj = self.add_pub_dbxref_object()
        obj = pub.PubDbxRef(pub_id=(existing_obj.pub_id+100), dbxref_id=existing_obj.dbxref_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_pub_dbxref_dbxref_id_fkey(self):
        # Test foreign key constraint on 'pub_dbxref.dbxref_id'
        existing_obj = self.add_pub_dbxref_object()
        obj = pub.PubDbxRef(pub_id=existing_obj.pub_id, dbxref_id=(existing_obj.dbxref_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_pub_dbxref_c1(self):
        # Test unique constraint on 'pub_dbxref.pub_id', 'pub_dbxref.dbxref_id'
        existing_obj = self.add_pub_dbxref_object()
        obj = pub.PubDbxRef(pub_id=existing_obj.pub_id, dbxref_id=existing_obj.dbxref_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'pub_relationship' table
    def add_pub_relationship_object(self) -> pub.PubRelationship:
        # Insert a random entry into the 'pub_relationship' table
        subject_obj = self.add_pub_object()
        object_obj = self.add_pub_object()
        type_obj = self.add_cvterm_object()
        pub_relationship_obj = pub.PubRelationship(subject_id=subject_obj.pub_id, object_id=object_obj.pub_id,
                                                   type_id=type_obj.cvterm_id)
        self.client.add_and_flush(pub_relationship_obj)
        return pub_relationship_obj

    def test_pub_relationship(self):
        # Test adding a new 'pub_relationship' object to the database
        existing_obj = self.add_pub_relationship_object()
        self.assertIsNotNone(existing_obj.pub_relationship_id)
        self.assertEqual(existing_obj.__tablename__, 'pub_relationship')

    def test_pub_relationship_type_id_fkey(self):
        # Test foreign key constraint on 'pub_relationship.type_id'
        existing_obj = self.add_pub_relationship_object()
        obj = pub.PubRelationship(subject_id=existing_obj.subject_id, object_id=existing_obj.object_id,
                                  type_id=(existing_obj.type_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_pub_relationship_subject_id_fkey(self):
        # Test foreign key constraint on 'pub_relationship.subject_id'
        existing_obj = self.add_pub_relationship_object()
        obj = pub.PubRelationship(subject_id=(existing_obj.subject_id+100), object_id=existing_obj.object_id,
                                  type_id=existing_obj.type_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_pub_relationship_object_id_fkey(self):
        # Test foreign key constraint on 'pub_relationship.object_id'
        existing_obj = self.add_pub_relationship_object()
        obj = pub.PubRelationship(subject_id=existing_obj.subject_id, object_id=(existing_obj.object_id+100),
                                  type_id=existing_obj.type_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_pub_relationship_c1(self):
        # Test unique constraint on 'pub_relationship.subject_id', 'pub_relationship.object_id',
        # 'pub_relationship.type_id'
        existing_obj = self.add_pub_relationship_object()
        obj = pub.PubRelationship(subject_id=existing_obj.subject_id, object_id=existing_obj.object_id,
                                  type_id=existing_obj.type_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'pubauthor' table
    def add_pubauthor_object(self) -> pub.PubAuthor:
        # Insert a random entry into the 'pub' table
        pub_obj = self.add_pub_object()
        pubauthor_obj = pub.PubAuthor(pub_id=pub_obj.pub_id, rank=utils.random_integer(100),
                                      surname=utils.random_string(10), givennames=utils.random_string(10),
                                      suffix=utils.random_string(10), editor=False)
        self.client.add_and_flush(pubauthor_obj)
        return pubauthor_obj

    def test_pubauthor(self):
        # Test adding a new 'pubauthor' object to the database
        existing_obj = self.add_pubauthor_object()
        self.assertIsNotNone(existing_obj.pubauthor_id)
        self.assertEqual(existing_obj.__tablename__, 'pubauthor')

    def test_pubauthor_pub_id_fkey(self):
        # Test foreign key constraint on 'pubauthor.pub_id'
        existing_obj = self.add_pubauthor_object()
        obj = pub.PubAuthor(pub_id=(existing_obj.pub_id+100), rank=utils.random_integer(100),
                            surname=utils.random_string(10))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_pubauthor_c1(self):
        # Test unique constraint on 'pubauthor.pub_id', 'pubauthor.rank'
        existing_obj = self.add_pubauthor_object()
        obj = pub.PubAuthor(pub_id=existing_obj.pub_id, rank=existing_obj.rank, surname=utils.random_string(10))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'pubprop' table
    def add_pubprop_object(self) -> pub.PubProp:
        # Insert a random entry into the 'pubprop' table
        pub_obj = self.add_pub_object()
        type_obj = self.add_cvterm_object()
        pubprop_obj = pub.PubProp(pub_id=pub_obj.pub_id, type_id=type_obj.cvterm_id, value=utils.random_string(10),
                                  rank=utils.random_integer(100))
        self.client.add_and_flush(pubprop_obj)
        return pubprop_obj

    def test_pubprop(self):
        # Test adding a new 'pubprop' object to the database
        existing_obj = self.add_pubprop_object()
        self.assertIsNotNone(existing_obj.pubprop_id)
        self.assertEqual(existing_obj.__tablename__, 'pubprop')

    def test_pubprop_pub_id_fkey(self):
        # Test foreign key constraint on 'pubprop.pub_id'
        existing_obj = self.add_pubprop_object()
        obj = pub.PubProp(pub_id=(existing_obj.pub_id+100), type_id=existing_obj.type_id,
                          rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_pubprop_type_id_fkey(self):
        # Test foreign key constraint on 'pubprop.type_id'
        existing_obj = self.add_pubprop_object()
        obj = pub.PubProp(pub_id=existing_obj.pub_id, type_id=(existing_obj.type_id+100),
                          rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_pubprop_c1(self):
        # Test unique constraint on 'pubprop.pub_id', 'pubprop.type_id', 'pubprop.rank'
        existing_obj = self.add_pubprop_object()
        obj = pub.PubProp(pub_id=existing_obj.pub_id, type_id=existing_obj.type_id, rank=existing_obj.rank)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'feature' table
    def add_feature_object(self) -> sequence.Feature:
        # Insert a random entry into the 'feature' table
        dbxref_obj = self.add_dbxref_object()
        organism_obj = self.add_organism_object()
        type_obj = self.add_cvterm_object()
        feature_obj = sequence.Feature(dbxref_id=dbxref_obj.dbxref_id, organism_id=organism_obj.organism_id,
                                       type_id=type_obj.cvterm_id, uniquename=utils.random_string(10),
                                       name=utils.random_string(10), residues=utils.random_string(10), seqlen=10,
                                       md5checksum=utils.random_string(10), is_analysis=False, is_obsolete=False)
        self.client.add_and_flush(feature_obj)
        return feature_obj

    def test_feature(self):
        # Test adding a new 'feature' object to the database
        existing_obj = self.add_feature_object()
        self.assertIsNotNone(existing_obj.feature_id)
        self.assertIsNotNone(existing_obj.timelastmodified)
        self.assertIsNotNone(existing_obj.timeaccessioned)
        self.assertEqual(existing_obj.__tablename__, 'feature')

    def test_feature_dbxref_id_fkey(self):
        # Test foreign key constraint on 'feature.dbxref_id'
        existing_obj = self.add_feature_object()
        obj = sequence.Feature(dbxref_id=(existing_obj.dbxref_id+100), organism_id=existing_obj.organism_id,
                               type_id=existing_obj.type_id, uniquename=utils.random_string(10))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_organism_id_fkey(self):
        # Test foreign key constraint on 'feature.organism_id'
        existing_obj = self.add_feature_object()
        obj = sequence.Feature(dbxref_id=existing_obj.dbxref_id, organism_id=(existing_obj.organism_id+100),
                               type_id=existing_obj.type_id, uniquename=utils.random_string(10))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_type_id_fkey(self):
        # Test foreign key constraint on 'feature.type_id'
        existing_obj = self.add_feature_object()
        obj = sequence.Feature(dbxref_id=existing_obj.dbxref_id, organism_id=existing_obj.organism_id,
                               type_id=(existing_obj.type_id+100), uniquename=utils.random_string(10))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_c1(self):
        # Test unique constraint on 'feature.organism_id', 'feature.type_id', 'feature.uniquename'
        existing_obj = self.add_feature_object()
        obj = sequence.Feature(dbxref_id=existing_obj.dbxref_id, organism_id=existing_obj.organism_id,
                               type_id=existing_obj.type_id, uniquename=existing_obj.uniquename)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'feature_cvterm' table
    def add_feature_cvterm_object(self) -> sequence.FeatureCvTerm:
        # Insert a random entry into the 'feature_cvterm' table
        feature_obj = self.add_feature_object()
        cvterm_obj = self.add_cvterm_object()
        pub_obj = self.add_pub_object()
        feature_cvterm_obj = sequence.FeatureCvTerm(feature_id=feature_obj.feature_id, cvterm_id=cvterm_obj.cvterm_id,
                                                    pub_id=pub_obj.pub_id, is_not=False, rank=utils.random_integer(100))
        self.client.add_and_flush(feature_cvterm_obj)
        return feature_cvterm_obj

    def test_feature_cvterm(self):
        # Test adding a new 'feature_cvterm' object to the database
        existing_obj = self.add_feature_cvterm_object()
        self.assertIsNotNone(existing_obj.feature_cvterm_id)
        self.assertEqual(existing_obj.__tablename__, 'feature_cvterm')

    def test_feature_cvterm_feature_id_fkey(self):
        # Test foreign key constraint on 'feature_cvterm.feature_id'
        existing_obj = self.add_feature_cvterm_object()
        obj = sequence.FeatureCvTerm(feature_id=(existing_obj.feature_id+100), cvterm_id=existing_obj.cvterm_id,
                                     pub_id=existing_obj.pub_id, rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_cvterm_cvterm_id_fkey(self):
        # Test foreign key constraint on 'feature_cvterm.cvterm_id'
        existing_obj = self.add_feature_cvterm_object()
        obj = sequence.FeatureCvTerm(feature_id=existing_obj.feature_id, cvterm_id=(existing_obj.cvterm_id+100),
                                     pub_id=existing_obj.pub_id, rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_cvterm_pub_id_fkey(self):
        # Test foreign key constraint on 'feature_cvterm.pub_id'
        existing_obj = self.add_feature_cvterm_object()
        obj = sequence.FeatureCvTerm(feature_id=existing_obj.feature_id, cvterm_id=existing_obj.cvterm_id,
                                     pub_id=(existing_obj.pub_id+100), rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_cvterm_c1(self):
        # Test unique constraint on 'feature_cvterm.feature_id', 'feature_cvterm.cvterm_id', 'feature_cvterm.pub_id',
        # 'feature_cvterm.rank'
        existing_obj = self.add_feature_cvterm_object()
        obj = sequence.FeatureCvTerm(feature_id=existing_obj.feature_id, cvterm_id=existing_obj.cvterm_id,
                                     pub_id=existing_obj.pub_id, rank=existing_obj.rank)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)
    
    # Test suite for the Chado 'feature_cvterm_dbxref' table
    def add_feature_cvterm_dbxref_object(self) -> sequence.FeatureCvTermDbxRef:
        # Insert a random entry into the 'feature_cvterm_dbxref' table
        feature_cvterm_obj = self.add_feature_cvterm_object()
        dbxref_obj = self.add_dbxref_object()
        feature_cvterm_dbxref_obj = sequence.FeatureCvTermDbxRef(feature_cvterm_id=feature_cvterm_obj.feature_cvterm_id,
                                                                 dbxref_id=dbxref_obj.dbxref_id)
        self.client.add_and_flush(feature_cvterm_dbxref_obj)
        return feature_cvterm_dbxref_obj

    def test_feature_cvterm_dbxref(self):
        # Test adding a new 'feature_cvterm_dbxref' object to the database
        existing_obj = self.add_feature_cvterm_dbxref_object()
        self.assertIsNotNone(existing_obj.feature_cvterm_dbxref_id)
        self.assertEqual(existing_obj.__tablename__, 'feature_cvterm_dbxref')

    def test_feature_cvterm_dbxref_feature_cvterm_id_fkey(self):
        # Test foreign key constraint on 'feature_cvterm_dbxref.feature_cvterm_id'
        existing_obj = self.add_feature_cvterm_dbxref_object()
        obj = sequence.FeatureCvTermDbxRef(feature_cvterm_id=(existing_obj.feature_cvterm_id+100),
                                           dbxref_id=existing_obj.dbxref_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_cvterm_dbxref_dbxref_id_fkey(self):
        # Test foreign key constraint on 'feature_cvterm_dbxref.dbxref_id'
        existing_obj = self.add_feature_cvterm_dbxref_object()
        obj = sequence.FeatureCvTermDbxRef(feature_cvterm_id=existing_obj.feature_cvterm_id,
                                           dbxref_id=(existing_obj.dbxref_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_cvterm_dbxref_c1(self):
        # Test unique constraint on 'feature_cvterm_dbxref.feature_cvterm_id', 'feature_cvterm_dbxref.dbxref_id'
        existing_obj = self.add_feature_cvterm_dbxref_object()
        obj = sequence.FeatureCvTermDbxRef(feature_cvterm_id=existing_obj.feature_cvterm_id,
                                           dbxref_id=existing_obj.dbxref_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'feature_cvtermprop' table
    def add_feature_cvtermprop_object(self) -> sequence.FeatureCvTermProp:
        # Insert a random entry into the 'feature_cvtermprop' table
        feature_cvterm_obj = self.add_feature_cvterm_object()
        type_obj = self.add_cvterm_object()
        feature_cvtermprop_obj = sequence.FeatureCvTermProp(feature_cvterm_id=feature_cvterm_obj.feature_cvterm_id,
                                                            type_id=type_obj.cvterm_id, value=utils.random_string(10),
                                                            rank=utils.random_integer(100))
        self.client.add_and_flush(feature_cvtermprop_obj)
        return feature_cvtermprop_obj

    def test_feature_cvtermprop(self):
        # Test adding a new 'feature_cvtermprop' object to the database
        existing_obj = self.add_feature_cvtermprop_object()
        self.assertIsNotNone(existing_obj.feature_cvtermprop_id)
        self.assertEqual(existing_obj.__tablename__, 'feature_cvtermprop')

    def test_feature_cvtermprop_feature_cvterm_id_fkey(self):
        # Test foreign key constraint on 'feature_cvtermprop.feature_cvterm_id'
        existing_obj = self.add_feature_cvtermprop_object()
        obj = sequence.FeatureCvTermProp(feature_cvterm_id=(existing_obj.feature_cvterm_id+100),
                                         type_id=existing_obj.type_id, value=utils.random_string(10),
                                         rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_cvtermprop_type_id_fkey(self):
        # Test foreign key constraint on 'feature_cvtermprop.type_id'
        existing_obj = self.add_feature_cvtermprop_object()
        obj = sequence.FeatureCvTermProp(feature_cvterm_id=existing_obj.feature_cvterm_id,
                                         type_id=(existing_obj.type_id+100), value=utils.random_string(10),
                                         rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_cvtermprop_c1(self):
        # Test unique constraint on 'feature_cvtermprop.feature_cvterm_id', 'feature_cvtermprop.type_id',
        # 'feature_cvtermprop.rank'
        existing_obj = self.add_feature_cvtermprop_object()
        obj = sequence.FeatureCvTermProp(feature_cvterm_id=existing_obj.feature_cvterm_id,
                                         type_id=existing_obj.type_id, rank=existing_obj.rank)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'feature_cvterm_pub' table
    def add_feature_cvterm_pub_object(self) -> sequence.FeatureCvTermPub:
        # Insert a random entry into the 'feature_cvterm_pub' table
        feature_cvterm_obj = self.add_feature_cvterm_object()
        pub_obj = self.add_pub_object()
        feature_cvterm_pub_obj = sequence.FeatureCvTermPub(feature_cvterm_id=feature_cvterm_obj.feature_cvterm_id,
                                                           pub_id=pub_obj.pub_id)
        self.client.add_and_flush(feature_cvterm_pub_obj)
        return feature_cvterm_pub_obj

    def test_feature_cvterm_pub(self):
        # Test adding a new 'feature_cvterm_pub' object to the database
        existing_obj = self.add_feature_cvterm_pub_object()
        self.assertIsNotNone(existing_obj.feature_cvterm_pub_id)
        self.assertEqual(existing_obj.__tablename__, 'feature_cvterm_pub')

    def test_feature_cvterm_pub_feature_cvterm_id_fkey(self):
        # Test foreign key constraint on 'feature_cvterm_pub.feature_cvterm_id'
        existing_obj = self.add_feature_cvterm_pub_object()
        obj = sequence.FeatureCvTermPub(feature_cvterm_id=(existing_obj.feature_cvterm_id+100),
                                        pub_id=existing_obj.pub_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_cvterm_pub_pub_id_fkey(self):
        # Test foreign key constraint on 'feature_cvterm_pub.pub_id'
        existing_obj = self.add_feature_cvterm_pub_object()
        obj = sequence.FeatureCvTermPub(feature_cvterm_id=existing_obj.feature_cvterm_id,
                                        pub_id=(existing_obj.pub_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_cvterm_pub_c1(self):
        # Test unique constraint on 'feature_cvterm_pub.feature_cvterm_id', 'feature_cvterm_pub.pub_id'
        existing_obj = self.add_feature_cvterm_pub_object()
        obj = sequence.FeatureCvTermPub(feature_cvterm_id=existing_obj.feature_cvterm_id,
                                        pub_id=existing_obj.pub_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'feature_dbxref' table
    def add_feature_dbxref_object(self) -> sequence.FeatureDbxRef:
        # Insert a random entry into the 'feature_dbxref' table
        feature_obj = self.add_feature_object()
        dbxref_obj = self.add_dbxref_object()
        feature_dbxref_obj = sequence.FeatureDbxRef(feature_id=feature_obj.feature_id, dbxref_id=dbxref_obj.dbxref_id, 
                                                    is_current=True)
        self.client.add_and_flush(feature_dbxref_obj)
        return feature_dbxref_obj

    def test_feature_dbxref(self):
        # Test adding a new 'feature_dbxref' object to the database
        existing_obj = self.add_feature_dbxref_object()
        self.assertIsNotNone(existing_obj.feature_dbxref_id)
        self.assertEqual(existing_obj.__tablename__, 'feature_dbxref')

    def test_feature_dbxref_feature_id_fkey(self):
        # Test foreign key constraint on 'feature_dbxref.feature_id'
        existing_obj = self.add_feature_dbxref_object()
        obj = sequence.FeatureDbxRef(feature_id=(existing_obj.feature_id+100), dbxref_id=existing_obj.dbxref_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_dbxref_dbxref_id_fkey(self):
        # Test foreign key constraint on 'feature_dbxref.dbxref_id'
        existing_obj = self.add_feature_dbxref_object()
        obj = sequence.FeatureDbxRef(feature_id=existing_obj.feature_id, dbxref_id=(existing_obj.dbxref_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_dbxref_c1(self):
        # Test unique constraint on 'feature_dbxref.feature_id', 'feature_dbxref.dbxref_id'
        existing_obj = self.add_feature_dbxref_object()
        obj = sequence.FeatureDbxRef(feature_id=existing_obj.feature_id, dbxref_id=existing_obj.dbxref_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)
            
    # Test suite for the Chado 'feature_pub' table
    def add_feature_pub_object(self) -> sequence.FeaturePub:
        # Insert a random entry into the 'feature_pub' table
        feature_obj = self.add_feature_object()
        pub_obj = self.add_pub_object()
        feature_pub_obj = sequence.FeaturePub(feature_id=feature_obj.feature_id, pub_id=pub_obj.pub_id)
        self.client.add_and_flush(feature_pub_obj)
        return feature_pub_obj

    def test_feature_pub(self):
        # Test adding a new 'feature_pub' object to the database
        existing_obj = self.add_feature_pub_object()
        self.assertIsNotNone(existing_obj.feature_pub_id)
        self.assertEqual(existing_obj.__tablename__, 'feature_pub')

    def test_feature_pub_feature_id_fkey(self):
        # Test foreign key constraint on 'feature_pub.feature_id'
        existing_obj = self.add_feature_pub_object()
        obj = sequence.FeaturePub(feature_id=(existing_obj.feature_id+100), pub_id=existing_obj.pub_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_pub_pub_id_fkey(self):
        # Test foreign key constraint on 'feature_pub.pub_id'
        existing_obj = self.add_feature_pub_object()
        obj = sequence.FeaturePub(feature_id=existing_obj.feature_id, pub_id=(existing_obj.pub_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_pub_c1(self):
        # Test unique constraint on 'feature_pub.feature_id', 'feature_pub.pub_id'
        existing_obj = self.add_feature_pub_object()
        obj = sequence.FeaturePub(feature_id=existing_obj.feature_id, pub_id=existing_obj.pub_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)
            
    # Test suite for the Chado 'feature_pubprop' table
    def add_feature_pubprop_object(self) -> sequence.FeaturePubProp:
        # Insert a random entry into the 'feature_pubprop' table
        feature_pub_obj = self.add_feature_pub_object()
        type_obj = self.add_cvterm_object()
        feature_pubprop_obj = sequence.FeaturePubProp(feature_pub_id=feature_pub_obj.feature_pub_id, 
                                                      type_id=type_obj.cvterm_id, value=utils.random_string(10), 
                                                      rank=utils.random_integer(100))
        self.client.add_and_flush(feature_pubprop_obj)
        return feature_pubprop_obj

    def test_feature_pubprop(self):
        # Test adding a new 'feature_pubprop' object to the database
        existing_obj = self.add_feature_pubprop_object()
        self.assertIsNotNone(existing_obj.feature_pubprop_id)
        self.assertEqual(existing_obj.__tablename__, 'feature_pubprop')

    def test_feature_pubprop_feature_pub_id_fkey(self):
        # Test foreign key constraint on 'feature_pubprop.feature_pub_id'
        existing_obj = self.add_feature_pubprop_object()
        obj = sequence.FeaturePubProp(feature_pub_id=(existing_obj.feature_pub_id+100), type_id=existing_obj.type_id,
                                      value=utils.random_string(10), rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_pubprop_type_id_fkey(self):
        # Test foreign key constraint on 'feature_pubprop.type_id'
        existing_obj = self.add_feature_pubprop_object()
        obj = sequence.FeaturePubProp(feature_pub_id=existing_obj.feature_pub_id, type_id=(existing_obj.type_id+100),
                                      value=utils.random_string(10), rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_pubprop_c1(self):
        # Test unique constraint on 'feature_pubprop.feature_pub_id', 'feature_pubprop.type_id', 'feature_pubprop.rank'
        existing_obj = self.add_feature_pubprop_object()
        obj = sequence.FeaturePubProp(feature_pub_id=existing_obj.feature_pub_id, type_id=existing_obj.type_id,
                                      rank=existing_obj.rank)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'feature_relationship' table
    def add_feature_relationship_object(self) -> sequence.FeatureRelationship:
        # Insert a random entry into the 'feature_relationship' table
        subject_obj = self.add_feature_object()
        object_obj = self.add_feature_object()
        type_obj = self.add_cvterm_object()
        feature_relationship_obj = sequence.FeatureRelationship(
            subject_id=subject_obj.feature_id, object_id=object_obj.feature_id, type_id=type_obj.cvterm_id,
            value=utils.random_string(10), rank=utils.random_integer(100))
        self.client.add_and_flush(feature_relationship_obj)
        return feature_relationship_obj

    def test_feature_relationship(self):
        # Test adding a new 'feature_relationship' object to the database
        existing_obj = self.add_feature_relationship_object()
        self.assertIsNotNone(existing_obj.feature_relationship_id)
        self.assertEqual(existing_obj.__tablename__, 'feature_relationship')

    def test_feature_relationship_type_id_fkey(self):
        # Test foreign key constraint on 'feature_relationship.type_id'
        existing_obj = self.add_feature_relationship_object()
        obj = sequence.FeatureRelationship(subject_id=existing_obj.subject_id, object_id=existing_obj.object_id,
                                           type_id=(existing_obj.type_id+100), rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_relationship_subject_id_fkey(self):
        # Test foreign key constraint on 'feature_relationship.subject_id'
        existing_obj = self.add_feature_relationship_object()
        obj = sequence.FeatureRelationship(subject_id=(existing_obj.subject_id+100), object_id=existing_obj.object_id,
                                           type_id=existing_obj.type_id, rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_relationship_object_id_fkey(self):
        # Test foreign key constraint on 'feature_relationship.object_id'
        existing_obj = self.add_feature_relationship_object()
        obj = sequence.FeatureRelationship(subject_id=existing_obj.subject_id, object_id=(existing_obj.object_id+100),
                                           type_id=existing_obj.type_id, rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_relationship_c1(self):
        # Test unique constraint on 'feature_relationship.subject_id', 'feature_relationship.object_id',
        # 'feature_relationship.type_id', 'feature_relationship.rank'
        existing_obj = self.add_feature_relationship_object()
        obj = sequence.FeatureRelationship(subject_id=existing_obj.subject_id, object_id=existing_obj.object_id,
                                           type_id=existing_obj.type_id, rank=existing_obj.rank)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'feature_relationship_pub' table
    def add_feature_relationship_pub_object(self) -> sequence.FeatureRelationshipPub:
        # Insert a random entry into the 'feature_relationship_pub' table
        feature_relationship_obj = self.add_feature_relationship_object()
        pub_obj = self.add_pub_object()
        feature_relationship_pub_obj = sequence.FeatureRelationshipPub(
            feature_relationship_id=feature_relationship_obj.feature_relationship_id, pub_id=pub_obj.pub_id)
        self.client.add_and_flush(feature_relationship_pub_obj)
        return feature_relationship_pub_obj

    def test_feature_relationship_pub(self):
        # Test adding a new 'feature_relationship_pub' object to the database
        existing_obj = self.add_feature_relationship_pub_object()
        self.assertIsNotNone(existing_obj.feature_relationship_pub_id)
        self.assertEqual(existing_obj.__tablename__, 'feature_relationship_pub')

    def test_feature_relationship_pub_feature_relationship_id_fkey(self):
        # Test foreign key constraint on 'feature_relationship_pub.feature_relationship_id'
        existing_obj = self.add_feature_relationship_pub_object()
        obj = sequence.FeatureRelationshipPub(feature_relationship_id=(existing_obj.feature_relationship_id+100),
                                              pub_id=existing_obj.pub_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_relationship_pub_pub_id_fkey(self):
        # Test foreign key constraint on 'feature_relationship_pub.pub_id'
        existing_obj = self.add_feature_relationship_pub_object()
        obj = sequence.FeatureRelationshipPub(feature_relationship_id=existing_obj.feature_relationship_id,
                                              pub_id=(existing_obj.pub_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_relationship_pub_c1(self):
        # Test unique constraint on 'feature_relationship_pub.feature_relationship_id',
        # 'feature_relationship_pub.pub_id'
        existing_obj = self.add_feature_relationship_pub_object()
        obj = sequence.FeatureRelationshipPub(feature_relationship_id=existing_obj.feature_relationship_id,
                                              pub_id=existing_obj.pub_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)
            
    # Test suite for the Chado 'feature_relationshipprop' table
    def add_feature_relationshipprop_object(self) -> sequence.FeatureRelationshipProp:
        # Insert a random entry into the 'feature_relationshipprop' table
        feature_relationship_obj = self.add_feature_relationship_object()
        type_obj = self.add_cvterm_object()
        feature_relationshipprop_obj = sequence.FeatureRelationshipProp(
            feature_relationship_id=feature_relationship_obj.feature_relationship_id, type_id=type_obj.cvterm_id,
            value=utils.random_string(10), rank=utils.random_integer(100))
        self.client.add_and_flush(feature_relationshipprop_obj)
        return feature_relationshipprop_obj

    def test_feature_relationshipprop(self):
        # Test adding a new 'feature_relationshipprop' object to the database
        existing_obj = self.add_feature_relationshipprop_object()
        self.assertIsNotNone(existing_obj.feature_relationshipprop_id)
        self.assertEqual(existing_obj.__tablename__, 'feature_relationshipprop')

    def test_feature_relationshipprop_feature_relationship_id_fkey(self):
        # Test foreign key constraint on 'feature_relationshipprop.feature_relationship_id'
        existing_obj = self.add_feature_relationshipprop_object()
        obj = sequence.FeatureRelationshipProp(feature_relationship_id=(existing_obj.feature_relationship_id+100),
                                               type_id=existing_obj.type_id, value=utils.random_string(10),
                                               rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_relationshipprop_type_id_fkey(self):
        # Test foreign key constraint on 'feature_relationshipprop.type_id'
        existing_obj = self.add_feature_relationshipprop_object()
        obj = sequence.FeatureRelationshipProp(feature_relationship_id=existing_obj.feature_relationship_id,
                                               type_id=(existing_obj.type_id+100), value=utils.random_string(10),
                                               rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_relationshipprop_c1(self):
        # Test unique constraint on 'feature_relationshipprop.feature_relationship_id',
        # 'feature_relationshipprop.type_id', 'feature_relationshipprop.rank'
        existing_obj = self.add_feature_relationshipprop_object()
        obj = sequence.FeatureRelationshipProp(feature_relationship_id=existing_obj.feature_relationship_id,
                                               type_id=existing_obj.type_id, rank=existing_obj.rank)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'feature_relationshipprop_pub' table
    def add_feature_relationshipprop_pub_object(self) -> sequence.FeatureRelationshipPropPub:
        # Insert a random entry into the 'feature_relationshipprop_pub' table
        feature_relationshipprop_obj = self.add_feature_relationshipprop_object()
        pub_obj = self.add_pub_object()
        feature_relationshipprop_pub_obj = sequence.FeatureRelationshipPropPub(
            feature_relationshipprop_id=feature_relationshipprop_obj.feature_relationshipprop_id, pub_id=pub_obj.pub_id)
        self.client.add_and_flush(feature_relationshipprop_pub_obj)
        return feature_relationshipprop_pub_obj

    def test_feature_relationshipprop_pub(self):
        # Test adding a new 'feature_relationshipprop_pub' object to the database
        existing_obj = self.add_feature_relationshipprop_pub_object()
        self.assertIsNotNone(existing_obj.feature_relationshipprop_pub_id)
        self.assertEqual(existing_obj.__tablename__, 'feature_relationshipprop_pub')

    def test_feature_relationshipprop_pub_feature_relationshipprop_id_fkey(self):
        # Test foreign key constraint on 'feature_relationshipprop_pub.feature_relationshipprop_id'
        existing_obj = self.add_feature_relationshipprop_pub_object()
        obj = sequence.FeatureRelationshipPropPub(
            feature_relationshipprop_id=(existing_obj.feature_relationshipprop_id+100), pub_id=existing_obj.pub_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_relationshipprop_pub_pub_id_fkey(self):
        # Test foreign key constraint on 'feature_relationshipprop_pub.pub_id'
        existing_obj = self.add_feature_relationshipprop_pub_object()
        obj = sequence.FeatureRelationshipPropPub(
            feature_relationshipprop_id=existing_obj.feature_relationshipprop_id, pub_id=(existing_obj.pub_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_relationshipprop_pub_c1(self):
        # Test unique constraint on 'feature_relationshipprop_pub.feature_relationshipprop_id',
        # 'feature_relationshipprop_pub.pub_id'
        existing_obj = self.add_feature_relationshipprop_pub_object()
        obj = sequence.FeatureRelationshipPropPub(
            feature_relationshipprop_id=existing_obj.feature_relationshipprop_id, pub_id=existing_obj.pub_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'synonym' table
    def add_synonym_object(self) -> sequence.Synonym:
        # Insert a random entry into the 'synonym' table
        type_obj = self.add_cvterm_object()
        synonym_obj = sequence.Synonym(name=utils.random_string(10), type_id=type_obj.cvterm_id,
                                       synonym_sgml=utils.random_string(10))
        self.client.add_and_flush(synonym_obj)
        return synonym_obj

    def test_synonym(self):
        # Test adding a new 'synonym' object to the database
        existing_obj = self.add_synonym_object()
        self.assertIsNotNone(existing_obj.synonym_id)
        self.assertEqual(existing_obj.__tablename__, 'synonym')

    def test_synonym_type_id_fkey(self):
        # Test foreign key constraint on 'synonym.type_id'
        existing_obj = self.add_synonym_object()
        obj = sequence.Synonym(name=utils.random_string(10), type_id=(existing_obj.type_id+100),
                               synonym_sgml=utils.random_string(10))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_synonym_c1(self):
        # Test unique constraint on 'synonym.name', 'synonym.type_id'
        existing_obj = self.add_synonym_object()
        obj = sequence.Synonym(name=existing_obj.name, type_id=existing_obj.type_id,
                               synonym_sgml=utils.random_string(10))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'feature_synonym' table
    def add_feature_synonym_object(self) -> sequence.FeatureSynonym:
        # Insert a random entry into the 'feature_synonym' table
        feature_obj = self.add_feature_object()
        synonym_obj = self.add_synonym_object()
        pub_obj = self.add_pub_object()
        feature_synonym_obj = sequence.FeatureSynonym(feature_id=feature_obj.feature_id,
                                                      synonym_id=synonym_obj.synonym_id, pub_id=pub_obj.pub_id,
                                                      is_current=True, is_internal=True)
        self.client.add_and_flush(feature_synonym_obj)
        return feature_synonym_obj

    def test_feature_synonym(self):
        # Test adding a new 'feature_synonym' object to the database
        existing_obj = self.add_feature_synonym_object()
        self.assertIsNotNone(existing_obj.feature_synonym_id)
        self.assertEqual(existing_obj.__tablename__, 'feature_synonym')

    def test_feature_synonym_feature_id_fkey(self):
        # Test foreign key constraint on 'feature_synonym.feature_id'
        existing_obj = self.add_feature_synonym_object()
        obj = sequence.FeatureSynonym(feature_id=(existing_obj.feature_id+100), synonym_id=existing_obj.synonym_id,
                                      pub_id=existing_obj.pub_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_synonym_synonym_id_fkey(self):
        # Test foreign key constraint on 'feature_synonym.synonym_id'
        existing_obj = self.add_feature_synonym_object()
        obj = sequence.FeatureSynonym(feature_id=existing_obj.feature_id, synonym_id=(existing_obj.synonym_id+100),
                                      pub_id=existing_obj.pub_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_synonym_pub_id_fkey(self):
        # Test foreign key constraint on 'feature_synonym.pub_id'
        existing_obj = self.add_feature_synonym_object()
        obj = sequence.FeatureSynonym(feature_id=existing_obj.feature_id, synonym_id=existing_obj.synonym_id,
                                      pub_id=(existing_obj.pub_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_feature_synonym_c1(self):
        # Test unique constraint on 'feature_synonym.feature_id', 'feature_synonym.synonym_id', 'feature_synonym.pub_id'
        existing_obj = self.add_feature_synonym_object()
        obj = sequence.FeatureSynonym(feature_id=existing_obj.feature_id, synonym_id=existing_obj.synonym_id,
                                      pub_id=existing_obj.pub_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'featureloc' table
    def add_featureloc_object(self) -> sequence.FeatureLoc:
        # Insert a random entry into the 'featureloc' table
        feature_obj = self.add_feature_object()
        srcfeature_obj = self.add_feature_object()
        fmin = utils.random_integer(100)
        fmax = fmin + utils.random_integer(100)
        featureloc_obj = sequence.FeatureLoc(feature_id=feature_obj.feature_id, srcfeature_id=srcfeature_obj.feature_id,
                                             fmin=fmin, is_fmin_partial=False, fmax=fmax, is_fmax_partial=False,
                                             strand=utils.random_integer(100), phase=utils.random_integer(100),
                                             residue_info=utils.random_string(10), locgroup=utils.random_integer(100),
                                             rank=utils.random_integer(100))
        self.client.add_and_flush(featureloc_obj)
        return featureloc_obj

    def test_featureloc(self):
        # Test adding a new 'featureloc' object to the database
        existing_obj = self.add_featureloc_object()
        self.assertIsNotNone(existing_obj.featureloc_id)
        self.assertEqual(existing_obj.__tablename__, 'featureloc')

    def test_featureloc_feature_id_fkey(self):
        # Test foreign key constraint on 'featureloc.feature_id'
        existing_obj = self.add_featureloc_object()
        fmin = utils.random_integer(100)
        fmax = fmin + utils.random_integer(100)
        obj = sequence.FeatureLoc(feature_id=(existing_obj.feature_id+100), srcfeature_id=existing_obj.srcfeature_id,
                                  fmin=fmin, fmax=fmax, locgroup=utils.random_integer(100),
                                  rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_featureloc_srcfeature_id_fkey(self):
        # Test foreign key constraint on 'featureloc.srcfeature_id'
        existing_obj = self.add_featureloc_object()
        fmin = utils.random_integer(100)
        fmax = fmin + utils.random_integer(100)
        obj = sequence.FeatureLoc(feature_id=existing_obj.feature_id, srcfeature_id=(existing_obj.srcfeature_id+100),
                                  fmin=fmin, fmax=fmax, locgroup=utils.random_integer(100),
                                  rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_featureloc_c1(self):
        # Test unique constraint on 'featureloc.feature_id', 'featureloc.locgroup', 'featureloc.rank'
        existing_obj = self.add_featureloc_object()
        fmin = utils.random_integer(100)
        fmax = fmin + utils.random_integer(100)
        obj = sequence.FeatureLoc(feature_id=existing_obj.feature_id, srcfeature_id=existing_obj.srcfeature_id,
                                  fmin=fmin, fmax=fmax, locgroup=existing_obj.locgroup, rank=existing_obj.rank)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_featureloc_c2(self):
        # Test check constraint on 'featureloc.fmin', 'featureloc.fmax'
        existing_obj = self.add_featureloc_object()
        fmax = utils.random_integer(100)
        fmin = fmax + 1 + utils.random_integer(100)
        obj = sequence.FeatureLoc(feature_id=existing_obj.feature_id, srcfeature_id=existing_obj.srcfeature_id,
                                  fmin=fmin, fmax=fmax, locgroup=utils.random_integer(100),
                                  rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'featureloc_pub' table
    def add_featureloc_pub_object(self) -> sequence.FeatureLocPub:
        # Insert a random entry into the 'featureloc_pub' table
        featureloc_obj = self.add_featureloc_object()
        pub_obj = self.add_pub_object()
        featureloc_pub_obj = sequence.FeatureLocPub(featureloc_id=featureloc_obj.featureloc_id, pub_id=pub_obj.pub_id)
        self.client.add_and_flush(featureloc_pub_obj)
        return featureloc_pub_obj

    def test_featureloc_pub(self):
        # Test adding a new 'featureloc_pub' object to the database
        existing_obj = self.add_featureloc_pub_object()
        self.assertIsNotNone(existing_obj.featureloc_pub_id)
        self.assertEqual(existing_obj.__tablename__, 'featureloc_pub')

    def test_featureloc_pub_featureloc_id_fkey(self):
        # Test foreign key constraint on 'featureloc_pub.featureloc_id'
        existing_obj = self.add_featureloc_pub_object()
        obj = sequence.FeatureLocPub(featureloc_id=(existing_obj.featureloc_id+100), pub_id=existing_obj.pub_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_featureloc_pub_pub_id_fkey(self):
        # Test foreign key constraint on 'featureloc_pub.pub_id'
        existing_obj = self.add_featureloc_pub_object()
        obj = sequence.FeatureLocPub(featureloc_id=existing_obj.featureloc_id, pub_id=(existing_obj.pub_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_featureloc_pub_c1(self):
        # Test unique constraint on 'featureloc_pub.featureloc_id', 'featureloc_pub.pub_id'
        existing_obj = self.add_featureloc_pub_object()
        obj = sequence.FeatureLocPub(featureloc_id=existing_obj.featureloc_id, pub_id=existing_obj.pub_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)
            
    # Test suite for the Chado 'featureprop' table
    def add_featureprop_object(self) -> sequence.FeatureProp:
        # Insert a random entry into the 'featureprop' table
        feature_obj = self.add_feature_object()
        type_obj = self.add_cvterm_object()
        featureprop_obj = sequence.FeatureProp(feature_id=feature_obj.feature_id, type_id=type_obj.cvterm_id,
                                               value=utils.random_string(10), rank=utils.random_integer(100))
        self.client.add_and_flush(featureprop_obj)
        return featureprop_obj

    def test_featureprop(self):
        # Test adding a new 'featureprop' object to the database
        existing_obj = self.add_featureprop_object()
        self.assertIsNotNone(existing_obj.featureprop_id)
        self.assertEqual(existing_obj.__tablename__, 'featureprop')

    def test_featureprop_feature_id_fkey(self):
        # Test foreign key constraint on 'featureprop.feature_id'
        existing_obj = self.add_featureprop_object()
        obj = sequence.FeatureProp(feature_id=(existing_obj.feature_id+100), type_id=existing_obj.type_id,
                                   value=utils.random_string(10), rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_featureprop_type_id_fkey(self):
        # Test foreign key constraint on 'featureprop.type_id'
        existing_obj = self.add_featureprop_object()
        obj = sequence.FeatureProp(feature_id=existing_obj.feature_id, type_id=(existing_obj.type_id+100),
                                   value=utils.random_string(10), rank=utils.random_integer(100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_featureprop_c1(self):
        # Test unique constraint on 'featureprop.feature_id', 'featureprop.type_id', 'featureprop.rank'
        existing_obj = self.add_featureprop_object()
        obj = sequence.FeatureProp(feature_id=existing_obj.feature_id, type_id=existing_obj.type_id,
                                   rank=existing_obj.rank)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'featureprop_pub' table
    def add_featureprop_pub_object(self) -> sequence.FeaturePropPub:
        # Insert a random entry into the 'featureprop_pub' table
        featureprop_obj = self.add_featureprop_object()
        pub_obj = self.add_pub_object()
        featureprop_pub_obj = sequence.FeaturePropPub(featureprop_id=featureprop_obj.featureprop_id,
                                                      pub_id=pub_obj.pub_id)
        self.client.add_and_flush(featureprop_pub_obj)
        return featureprop_pub_obj

    def test_featureprop_pub(self):
        # Test adding a new 'featureprop_pub' object to the database
        existing_obj = self.add_featureprop_pub_object()
        self.assertIsNotNone(existing_obj.featureprop_pub_id)
        self.assertEqual(existing_obj.__tablename__, 'featureprop_pub')

    def test_featureprop_pub_featureprop_id_fkey(self):
        # Test foreign key constraint on 'featureprop_pub.featureprop_id'
        existing_obj = self.add_featureprop_pub_object()
        obj = sequence.FeaturePropPub(featureprop_id=(existing_obj.featureprop_id+100), pub_id=existing_obj.pub_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_featureprop_pub_pub_id_fkey(self):
        # Test foreign key constraint on 'featureprop_pub.pub_id'
        existing_obj = self.add_featureprop_pub_object()
        obj = sequence.FeaturePropPub(featureprop_id=existing_obj.featureprop_id, pub_id=(existing_obj.pub_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_featureprop_pub_c1(self):
        # Test unique constraint on 'featureprop_pub.featureprop_id', 'featureprop_pub.pub_id'
        existing_obj = self.add_featureprop_pub_object()
        obj = sequence.FeaturePropPub(featureprop_id=existing_obj.featureprop_id, pub_id=existing_obj.pub_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'analysis' table
    def add_analysis_object(self) -> companalysis.Analysis:
        # Insert a random entry into the 'analysis' table
        analysis_obj = companalysis.Analysis(program=utils.random_string(10), programversion=utils.random_string(10),
                                             name=utils.random_string(10), description=utils.random_string(10),
                                             algorithm=utils.random_string(10), sourcename=utils.random_string(10),
                                             sourceversion=utils.random_string(10), sourceuri=utils.random_string(10))
        self.client.add_and_flush(analysis_obj)
        return analysis_obj

    def test_analysis(self):
        # Test adding a new 'analysis' object to the database
        existing_obj = self.add_analysis_object()
        self.assertIsNotNone(existing_obj.analysis_id)
        self.assertEqual(existing_obj.__tablename__, 'analysis')

    def test_analysis_c1(self):
        # Test unique constraint on 'analysis.program', 'analysis.programversion', 'analysis.sourcename'
        existing_obj = self.add_analysis_object()
        obj = companalysis.Analysis(program=existing_obj.program, programversion=existing_obj.programversion,
                                    sourcename=existing_obj.sourcename)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'analysisfeature' table
    def add_analysisfeature_object(self) -> companalysis.AnalysisFeature:
        # Insert a random entry into the 'analysisfeature' table
        analysis_obj = self.add_analysis_object()
        feature_obj = self.add_feature_object()
        analysisfeature_obj = companalysis.AnalysisFeature(
            feature_id=feature_obj.feature_id, analysis_id=analysis_obj.analysis_id, rawscore=utils.random_float(),
            normscore=utils.random_float(), significance=utils.random_float(), identity=utils.random_float())
        self.client.add_and_flush(analysisfeature_obj)
        return analysisfeature_obj

    def test_analysisfeature(self):
        # Test adding a new 'analysisfeature' object to the database
        existing_obj = self.add_analysisfeature_object()
        self.assertIsNotNone(existing_obj.analysisfeature_id)
        self.assertEqual(existing_obj.__tablename__, 'analysisfeature')

    def test_analysisfeature_feature_id_fkey(self):
        # Test foreign key constraint on 'analysisfeature.feature_id'
        existing_obj = self.add_analysisfeature_object()
        obj = companalysis.AnalysisFeature(feature_id=(existing_obj.feature_id+100),
                                           analysis_id=existing_obj.analysis_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_analysisfeature_analysis_id_fkey(self):
        # Test foreign key constraint on 'analysisfeature.analysis_id'
        existing_obj = self.add_analysisfeature_object()
        obj = companalysis.AnalysisFeature(feature_id=existing_obj.feature_id,
                                           analysis_id=(existing_obj.analysis_id+100))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_analysisfeature_c1(self):
        # Test unique constraint on 'analysisfeature.feature_id', 'analysisfeature.analysis_id'
        existing_obj = self.add_analysisfeature_object()
        obj = companalysis.AnalysisFeature(feature_id=existing_obj.feature_id, analysis_id=existing_obj.analysis_id)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    # Test suite for the Chado 'analysisprop' table
    def add_analysisprop_object(self) -> companalysis.AnalysisProp:
        # Insert a random entry into the 'analysisprop' table
        analysis_obj = self.add_analysis_object()
        type_obj = self.add_cvterm_object()
        analysisprop_obj = companalysis.AnalysisProp(analysis_id=analysis_obj.analysis_id, type_id=type_obj.cvterm_id,
                                                     value=utils.random_string(10))
        self.client.add_and_flush(analysisprop_obj)
        return analysisprop_obj

    def test_analysisprop(self):
        # Test adding a new 'analysisprop' object to the database
        existing_obj = self.add_analysisprop_object()
        self.assertIsNotNone(existing_obj.analysisprop_id)
        self.assertEqual(existing_obj.__tablename__, 'analysisprop')

    def test_analysisprop_analysis_id_fkey(self):
        # Test foreign key constraint on 'analysisprop.analysis_id'
        existing_obj = self.add_analysisprop_object()
        obj = companalysis.AnalysisProp(analysis_id=(existing_obj.analysis_id+100), type_id=existing_obj.type_id,
                                        value=utils.random_string(10))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_analysisprop_type_id_fkey(self):
        # Test foreign key constraint on 'analysisprop.type_id'
        existing_obj = self.add_analysisprop_object()
        obj = companalysis.AnalysisProp(analysis_id=existing_obj.analysis_id, type_id=(existing_obj.type_id+100),
                                        value=utils.random_string(10))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)

    def test_analysisprop_c1(self):
        # Test unique constraint on 'analysisprop.analysis_id', 'analysisprop.type_id', 'analysisprop.value'
        existing_obj = self.add_analysisprop_object()
        obj = companalysis.AnalysisProp(analysis_id=existing_obj.analysis_id, type_id=existing_obj.type_id,
                                        value=existing_obj.value)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.client.add_and_flush(obj)


class TestAudit(unittest.TestCase):
    """Base class for testing the setup of the master table defined in the 'audit' schema of the ORM"""

    connection_parameters = utils.parse_yaml(dbutils.default_configuration_file())
    connection_uri = dbutils.random_database_uri(connection_parameters)

    @classmethod
    def setUpClass(cls):
        # Creates a database, establishes a connection and creates schema and tables
        dbutils.create_database(cls.connection_uri)
        cls.client = iobase.IOClient(cls.connection_uri)
        schema_base = base.AuditBase
        schema_metadata = schema_base.metadata
        sqlalchemy.schema.CreateSchema('audit').execute(cls.client.engine)
        schema_base.metadata.create_all(cls.client.engine, tables=schema_metadata.sorted_tables)

    @classmethod
    def tearDownClass(cls):
        # Drops the database
        dbutils.drop_database(cls.connection_uri, True)

    def tearDown(self):
        # Rolls back all changes to the database
        self.client.session.rollback()

    def add_audit_object(self) -> audit.Audit:
        # Insert a random entry into the 'audit' table
        audit_obj = audit.Audit(type='INSERT')
        self.client.add_and_flush(audit_obj)
        return audit_obj

    def test_audit(self):
        # Test adding a new 'audit' object to the database
        existing_obj = self.add_audit_object()
        self.assertIsNotNone(existing_obj.audit_id)
        self.assertIsNotNone(existing_obj.username)
        self.assertIsNotNone(existing_obj.time)
        self.assertEqual(existing_obj.__tablename__, 'audit')

    def test_audit_type_constraint(self):
        # Test constraint on 'audit.type'
        obj = audit.Audit(type='NONEXISTENT_TYPE', username=utils.random_string(10))
        with self.assertRaises(sqlalchemy.exc.DataError):
            self.client.add_and_flush(obj)


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
