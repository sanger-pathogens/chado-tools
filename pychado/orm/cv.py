import sqlalchemy.orm
from pychado.orm.base import Base, BIGINT
from pychado.orm.general import DbxRef

# Object-relational mappings for the CHADO Controlled Vocabulary (CV) module


class Cv(Base):
    """Class for the CHADO 'cv' table"""
    # Columns
    cv_id = sqlalchemy.Column(BIGINT, nullable=False, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=False)
    definition = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)

    # Constraints
    __tablename__ = "cv"
    __table_args__ = (sqlalchemy.UniqueConstraint(name, name="cv_c1"),)

    # Initialisation
    def __init__(self, name, definition=None, cv_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<cv.Cv(cv_id={0}, name='{1}', definition='{2}')>".format(self.cv_id, self.name, self.definition)


class CvTerm(Base):
    """Class for the CHADO 'cvterm' table"""
    # Columns
    cvterm_id = sqlalchemy.Column(BIGINT, nullable=False, primary_key=True, autoincrement=True)
    cv_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Cv.cv_id, onupdate="CASCADE", ondelete="CASCADE", deferrable=True, initially="DEFERRED"), nullable=False)
    dbxref_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        DbxRef.dbxref_id, onupdate="CASCADE", ondelete="CASCADE", deferrable=True, initially="DEFERRED"),
                                  nullable=False)
    name = sqlalchemy.Column(sqlalchemy.VARCHAR(1024), nullable=False)
    definition = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)
    is_obsolete = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")
    is_relationshiptype = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")

    # Constraints
    __tablename__ = "cvterm"
    __table_args__ = (sqlalchemy.UniqueConstraint(name, cv_id, is_obsolete, name="cvterm_c1"),
                      sqlalchemy.UniqueConstraint(dbxref_id, name="cvterm_c2"),
                      sqlalchemy.Index("cvterm_idx1", cv_id),
                      sqlalchemy.Index("cvterm_idx2", name),
                      sqlalchemy.Index("cvterm_idx3", dbxref_id))
    
    # Relationships
    dbxref = sqlalchemy.orm.relationship(DbxRef, backref="cvterm_dbxref")
    cv = sqlalchemy.orm.relationship(Cv, backref="cvterm_cv")

    # Initialisation
    def __init__(self, cv_id, dbxref_id, name, definition=None, is_obsolete=0, is_relationshiptype=0, cvterm_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<cv.CvTerm(cvterm_id={0}, cv_id={1}, dbxref_id={2}, name='{3}', definition='{4}', is_obsolete={5}, " \
               "is_relationshiptype={6})>".format(self.cvterm_id, self.cv_id, self.dbxref_id, self.name,
                                                  self.definition, self.is_obsolete, self.is_relationshiptype)

    # Comparison
    def __eq__(self, other):
        if isinstance(other, CvTerm) \
                and self.cv_id == other.cv_id \
                and self.dbxref_id == other.dbxref_id \
                and self.name == other.name \
                and self.definition == other.definition \
                and self.is_obsolete == other.is_obsolete \
                and self.is_relationshiptype == other.is_relationshiptype:
            return True
        return False

    def __ne__(self, other):
        return not self == other


class CvTermProp(Base):
    """Class for the CHADO 'cvtermprop' table"""
    # Columns
    cvtermprop_id = sqlalchemy.Column(BIGINT, nullable=False, primary_key=True, autoincrement=True)
    cvterm_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    value = sqlalchemy.Column(sqlalchemy.TEXT, nullable=False, server_default=sqlalchemy.text("''"))
    rank = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")

    # Constraints
    __tablename__ = "cvtermprop"
    __table_args__ = (sqlalchemy.UniqueConstraint(cvterm_id, type_id, value, rank, name="cvtermprop_c1"),
                      sqlalchemy.Index("cvtermprop_idx1", cvterm_id),
                      sqlalchemy.Index("cvtermprop_idx2", type_id))

    # Relationships
    cvterm = sqlalchemy.orm.relationship(CvTerm, foreign_keys=cvterm_id, backref="cvtermprop_cvterm")
    type = sqlalchemy.orm.relationship(CvTerm, foreign_keys=type_id, backref="cvtermprop_type")

    # Initialisation
    def __init__(self, cvterm_id, type_id, value="", rank=0, cvtermprop_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<cv.CvTermProp(cvtermprop_id={0}, cvterm_id={1}, type_id={2}, value='{3}', rank={4})>"\
            .format(self.cvtermprop_id, self.cvterm_id, self.type_id, self.value, self.rank)


class CvTermRelationship(Base):
    """Class for the CHADO 'cvterm_relationship' table"""
    # Columns
    cvterm_relationship_id = sqlalchemy.Column(BIGINT, nullable=False, primary_key=True, autoincrement=True)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    subject_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    object_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    # Constraints
    __tablename__ = "cvterm_relationship"
    __table_args__ = (sqlalchemy.UniqueConstraint(subject_id, object_id, type_id, name="cvterm_relationship_c1"),
                      sqlalchemy.Index("cvterm_relationship_idx1", type_id),
                      sqlalchemy.Index("cvterm_relationship_idx2", subject_id),
                      sqlalchemy.Index("cvterm_relationship_idx3", object_id))

    # Relationships
    type = sqlalchemy.orm.relationship(CvTerm, foreign_keys=type_id, backref="cvterm_relationship_type")
    subject = sqlalchemy.orm.relationship(CvTerm, foreign_keys=subject_id, backref="cvterm_relationship_subject")
    object = sqlalchemy.orm.relationship(CvTerm, foreign_keys=object_id, backref="cvterm_relationship_object")

    # Initialisation
    def __init__(self, type_id, subject_id, object_id, cvterm_relationship_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<cv.CvTermRelationship(cvterm_relationship_id={0}, type_id={1}, subject_id={2}, object_id={3})>"\
            .format(self.cvterm_relationship_id, self.type_id, self.subject_id, self.object_id)


class CvTermSynonym(Base):
    """Class for the CHADO 'cvtermsynonym' table"""
    # Columns
    cvtermsynonym_id = sqlalchemy.Column(BIGINT, nullable=False, primary_key=True, autoincrement=True)
    cvterm_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    synonym = sqlalchemy.Column(sqlalchemy.VARCHAR(1024), nullable=False)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=True)

    # Constraints
    __tablename__ = "cvtermsynonym"
    __table_args__ = (sqlalchemy.UniqueConstraint(cvterm_id, synonym, name="cvtermsynonym_c1"),
                      sqlalchemy.Index("cvtermsynonym_idx1", cvterm_id))

    # Relationships
    cvterm = sqlalchemy.orm.relationship(CvTerm, foreign_keys=cvterm_id, backref="cvtermsynonym_cvterm")
    type = sqlalchemy.orm.relationship(CvTerm, foreign_keys=type_id, backref="cvtermsynonym_type")

    # Initialisation
    def __init__(self, cvterm_id, synonym, type_id=None, cvtermsynonym_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<cv.CvTermSynonym(cvtermsynonym_id={0}, cvterm_id={1}, synonym='{2}', type_id={3})>"\
            .format(self.cvtermsynonym_id, self.cvterm_id, self.synonym, self.type_id)


class CvTermDbxRef(Base):
    """Class for the CHADO 'cvterm_dbxref' table"""
    # Columns
    cvterm_dbxref_id = sqlalchemy.Column(BIGINT, nullable=False, primary_key=True, autoincrement=True)
    cvterm_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    dbxref_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        DbxRef.dbxref_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    is_for_definition = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")

    # Constraints
    __tablename__ = "cvterm_dbxref"
    __table_args__ = (sqlalchemy.UniqueConstraint(cvterm_id, dbxref_id, name="cvterm_dbxref_c1"),
                      sqlalchemy.Index("cvterm_dbxref_idx1", cvterm_id),
                      sqlalchemy.Index("cvterm_dbxref_idx2", dbxref_id))

    # Relationships
    cvterm = sqlalchemy.orm.relationship(CvTerm, foreign_keys=cvterm_id, backref="cvterm_dbxref_cvterm")
    dbxref = sqlalchemy.orm.relationship(DbxRef, foreign_keys=dbxref_id, backref="cvterm_dbxref_dbxref")

    # Initialisation
    def __init__(self, cvterm_id, dbxref_id, is_for_definition=0, cvterm_dbxref_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<cv.CvTermDbxRef(cvterm_dbxref_id={0}, cvterm_id={1}, dbxref_id={2}, is_for_definition={3})>"\
            .format(self.cvterm_dbxref_id, self.cvterm_id, self.dbxref_id, self.is_for_definition)
