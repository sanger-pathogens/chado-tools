import sqlalchemy.orm


class DatabaseError(Exception):
    pass


class InputFileError(Exception):
    pass


class DatabaseLoader:

    def __init__(self, uri: str):
        """Constructor - connect to database"""
        self.engine = sqlalchemy.create_engine(uri)                                 # type: sqlalchemy.engine.Engine
        session_maker = sqlalchemy.orm.sessionmaker(bind=self.engine)
        self.session = session_maker()                                              # type: sqlalchemy.orm.Session

    def __del__(self):
        """Destructor - disconnect from database"""
        self.session.close()

    def query_table(self, table, **kwargs) -> sqlalchemy.orm.Query:
        """Creates a query on a database table from given keyword arguments"""
        query = self.session.query(table)
        if kwargs:
            query = query.filter_by(**kwargs)
        return query

    def insert_into_table(self, table, **kwargs):
        """Creates an entry and inserts it into a database table"""
        obj = table(**kwargs)
        self.session.add(obj)
        self.session.flush()
        return obj

    def find_or_insert(self, table, **kwargs):
        """Returns one entry of a database table matching a query. If no matching entry exists, it is created."""
        entry = self.query_table(table, **kwargs).first()
        if not entry:
            entry = self.insert_into_table(table, **kwargs)
        return entry

    def commit(self):
        """Commits all changes"""
        self.session.commit()

    def rollback(self):
        """Rolls back all changes"""
        self.session.rollback()
