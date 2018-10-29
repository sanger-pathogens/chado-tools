import sqlalchemy.orm
from .. import ddl


class DatabaseError(Exception):
    pass


class InputFileError(Exception):
    pass


class IOClient(ddl.ChadoClient):
    """Base class for read-write access to a CHADO database"""

    def __init__(self, uri: str):
        """Constructor - connect to database"""
        super().__init__(uri)
        session_maker = sqlalchemy.orm.sessionmaker(bind=self.engine)
        self.session = session_maker()                                              # type: sqlalchemy.orm.Session

    def __del__(self):
        """Destructor - disconnect from database"""
        self.session.close()
        super().__del__()

    def query_table(self, table, **kwargs) -> sqlalchemy.orm.Query:
        """Creates a query on a database table from given keyword arguments"""
        query = self.session.query(table)
        if kwargs:
            query = query.filter_by(**kwargs)
        return query

    def add_and_flush(self, obj):
        """Adds an entry to a database table"""
        self.session.add(obj)
        self.session.flush()

    def insert_into_table(self, table, **kwargs):
        """Creates an entry and inserts it into a database table"""
        obj = table(**kwargs)
        self.add_and_flush(obj)
        return obj

    def find_or_insert(self, table, **kwargs):
        """Returns one entry of a database table matching a query. If no matching entry exists, it is created."""
        entry = self.query_table(table, **kwargs).first()
        if not entry:
            entry = self.insert_into_table(table, **kwargs)
        return entry
