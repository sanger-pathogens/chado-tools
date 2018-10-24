import sqlalchemy.orm
from . import base

# Object-relational mappings for the CHADO General module


class Db(base.PublicBase):
    """Class for the CHADO 'db' table"""
    # Columns
    db_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=False)
    description = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    urlprefix = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    url = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)

    # Constraints
    __tablename__ = "db"
    __table_args__ = (sqlalchemy.UniqueConstraint(name, name="db_c1"), )

    # Initialisation
    def __init__(self, name, description=None, urlprefix=None, url=None, db_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<general.Db(db_id={0}, name='{1}', description='{2}', urlprefix='{3}', url='{4}')>"\
            .format(self.db_id, self.name, self.description, self.urlprefix, self.url)


class DbxRef(base.PublicBase):
    """Class for the CHADO 'dbxref' table"""
    # Columns
    dbxref_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    db_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Db.db_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    accession = sqlalchemy.Column(sqlalchemy.VARCHAR(1024), nullable=False)
    version = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=False, server_default=sqlalchemy.text("''"))
    description = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)

    # Constraints
    __tablename__ = "dbxref"
    __table_args__ = (sqlalchemy.UniqueConstraint(db_id, accession, version, name="dbxref_c1"),
                      sqlalchemy.Index("dbxref_idx1", db_id),
                      sqlalchemy.Index("dbxref_idx2", accession),
                      sqlalchemy.Index("dbxref_idx3", version))

    # Relationships
    db = sqlalchemy.orm.relationship(Db, backref="dbxref_db")

    # Initialisation
    def __init__(self, db_id, accession, version="", description=None, dbxref_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<general.DbxRef(dbxref_id={0}, db_id={1}, accession='{2}', version='{3}', description='{4}')>"\
            .format(self.dbxref_id, self.db_id, self.accession, self.version, self.description)
