import sqlalchemy.orm


def find_or_create(session: sqlalchemy.orm.Session, table, **kwargs):
    """Returns one entry of a database table matching a query. If no matching entry exists, it is created."""
    result = session.query(table).filter_by(**kwargs).all()
    if result:
        return result[0]
    else:
        obj = table(**kwargs)
        session.add(obj)
        session.flush()
        return obj


def find(session: sqlalchemy.orm.Session, table, **kwargs) -> sqlalchemy.orm.Query:
    """Creates a query on a database table from given keyword arguments"""
    if kwargs:
        query = session.query(table).filter_by(**kwargs)
    else:
        query = session.query(table)
    return query
