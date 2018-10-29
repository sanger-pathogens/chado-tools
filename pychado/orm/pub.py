import sqlalchemy.orm
from . import base, general, cv

# Object-relational mappings for the CHADO Publication module


class Pub(base.PublicBase):
    """Class for the CHADO 'pub' table"""
    # Columns
    pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)
    volumetitle = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)
    volume = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    series_name = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    issue = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    pyear = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    pages = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    miniref = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    uniquename = sqlalchemy.Column(sqlalchemy.TEXT, nullable=False)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        cv.CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    is_obsolete = sqlalchemy.Column(sqlalchemy.BOOLEAN, nullable=False, server_default="False")
    publisher = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    pubplace = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)

    # Constraints
    __tablename__ = "pub"
    __table_args__ = (sqlalchemy.UniqueConstraint(uniquename, name="pub_c1"),
                      sqlalchemy.Index("pub_idx1", type_id))

    # Relationships
    type = sqlalchemy.orm.relationship(cv.CvTerm, foreign_keys=type_id, backref="pub_type")

    # Initialisation
    def __init__(self, uniquename, type_id, title=None, volumetitle=None, volume=None, series_name=None, issue=None,
                 pyear=None, pages=None, miniref=None, is_obsolete=False, publisher=None, pubplace=None, pub_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<pub.Pub(pub_id={0}, title='{1}', volumetitle='{2}', volume='{3}', series_name='{4}', issue='{5}', " \
               "pyear={6}, pages='{7}', miniref='{8}', uniquename='{9}', type_id={10}, is_obsolete={11}, " \
               "publisher='{12}', pubplace='{13}')>"\
            .format(self.pub_id, self.title, self.volumetitle, self.volume, self.series_name, self.issue, self.pyear,
                    self.pages, self.miniref, self.uniquename, self.type_id, self.is_obsolete, self.publisher,
                    self.pubplace)


class PubDbxRef(base.PublicBase):
    """Class for the CHADO 'pub_dbxref' table"""
    # Columns
    pub_dbxref_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Pub.pub_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    dbxref_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        general.DbxRef.dbxref_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    is_current = sqlalchemy.Column(sqlalchemy.BOOLEAN, nullable=False, server_default="True")

    # Constraints
    __tablename__ = "pub_dbxref"
    __table_args__ = (sqlalchemy.UniqueConstraint(pub_id, dbxref_id, name="pub_dbxref_c1"),
                      sqlalchemy.Index("pub_dbxref_idx1", pub_id),
                      sqlalchemy.Index("pub_dbxref_idx2", dbxref_id))

    # Relationships
    pub = sqlalchemy.orm.relationship(Pub, foreign_keys=pub_id, backref="pub_dbxref_pub")
    dbxref = sqlalchemy.orm.relationship(general.DbxRef, foreign_keys=dbxref_id, backref="pub_dbxref_dbxref")

    # Initialisation
    def __init__(self, pub_id, dbxref_id, is_current=True, pub_dbxref_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<pub.PubDbxRef(pub_dbxref_id={0}, pub_id={1}, dbxref_id={2}, is_current={3})>".format(
            self.pub_dbxref_id, self.pub_id, self.dbxref_id, self.is_current)


class PubRelationship(base.PublicBase):
    """Class for the CHADO 'pub_relationship' table"""
    # Columns
    pub_relationship_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    subject_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Pub.pub_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    object_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Pub.pub_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        cv.CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    # Constraints
    __tablename__ = "pub_relationship"
    __table_args__ = (sqlalchemy.UniqueConstraint(subject_id, object_id, type_id, name="pub_relationship_c1"),
                      sqlalchemy.Index("pub_relationship_idx1", subject_id),
                      sqlalchemy.Index("pub_relationship_idx2", object_id),
                      sqlalchemy.Index("pub_relationship_idx3", type_id))

    # Relationships
    type = sqlalchemy.orm.relationship(cv.CvTerm, foreign_keys=type_id, backref="pub_relationship_type")
    subject = sqlalchemy.orm.relationship(Pub, foreign_keys=subject_id, backref="pub_relationship_subject")
    object = sqlalchemy.orm.relationship(Pub, foreign_keys=object_id, backref="pub_relationship_object")

    # Initialisation
    def __init__(self, subject_id, object_id, type_id, pub_relationship_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<pub.PubRelationship(pub_relationship_id={0}, subject_id={1}, object_id={2}, type_id={3})>".format(
            self.pub_relationship_id, self.subject_id, self.object_id, self.type_id)


class PubAuthor(base.PublicBase):
    """Class for the CHADO 'pubauthor' table"""
    # Columns
    pubauthor_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Pub.pub_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    rank = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False)
    editor = sqlalchemy.Column(sqlalchemy.BOOLEAN, nullable=False, server_default="False")
    surname = sqlalchemy.Column(sqlalchemy.VARCHAR(100), nullable=False)
    givennames = sqlalchemy.Column(sqlalchemy.VARCHAR(100), nullable=True)
    suffix = sqlalchemy.Column(sqlalchemy.VARCHAR(100), nullable=True)

    # Constraints
    __tablename__ = "pubauthor"
    __table_args__ = (sqlalchemy.UniqueConstraint(pub_id, rank, name="pubauthor_c1"),
                      sqlalchemy.Index("pubauthor_idx2", pub_id))

    # Relationships
    pub = sqlalchemy.orm.relationship(Pub, foreign_keys=pub_id, backref="pubauthor_pub")

    # Initialisation
    def __init__(self, pub_id, rank, surname, givennames=None, suffix=None, editor=False, pubauthor_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<pub.PubAuthor(pubauthor_id={0}, pub_id={1}, rank={2}, editor={3}, surname='{4}', givennames='{5}', " \
               "suffix='{6}')>".format(self.pubauthor_id, self.pub_id, self.rank, self.editor, self.surname,
                                       self.givennames, self.suffix)


class PubProp(base.PublicBase):
    """Class for the CHADO 'pubprop' table"""
    # Columns
    pubprop_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Pub.pub_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        cv.CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    value = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)
    rank = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")

    # Constraints
    __tablename__ = "pubprop"
    __table_args__ = (sqlalchemy.UniqueConstraint(pub_id, type_id, rank, name="pubprop_c1"),
                      sqlalchemy.Index("pubprop_idx1", pub_id),
                      sqlalchemy.Index("pubprop_idx2", type_id))

    # Relationships
    pub = sqlalchemy.orm.relationship(Pub, foreign_keys=pub_id, backref="pubprop_pub")
    type = sqlalchemy.orm.relationship(cv.CvTerm, foreign_keys=type_id, backref="pubprop_type")

    # Initialisation
    def __init__(self, pub_id, type_id, value=None, rank=0, pubprop_id=None):
        for key, val in locals().items():
            if key != self:
                setattr(self, key, val)

    # Representation
    def __repr__(self):
        return "<pub.PubProp(pubprop_id={0}, pub_id={1}, type_id={2}, value='{3}', rank={4})>".format(
            self.pubprop_id, self.pub_id, self.type_id, self.value, self.rank)
