import sqlalchemy.orm
import sqlalchemy.sql.functions
from . import base, general, cv, organism, pub

# Object-relational mappings for the CHADO Sequence/Feature module


class Feature(base.PublicBase):
    """Class for the CHADO 'feature' table"""
    # Columns
    feature_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    dbxref_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        general.DbxRef.dbxref_id, onupdate="CASCADE", ondelete="SET NULL"), nullable=True)
    organism_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        organism.Organism.organism_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    name = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    uniquename = sqlalchemy.Column(sqlalchemy.TEXT, nullable=False)
    residues = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)
    seqlen = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=True)
    md5checksum = sqlalchemy.Column(sqlalchemy.CHAR(32), nullable=True)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        cv.CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    is_analysis = sqlalchemy.Column(sqlalchemy.BOOLEAN, nullable=False, server_default="False")
    is_obsolete = sqlalchemy.Column(sqlalchemy.BOOLEAN, nullable=False, server_default="False")
    timeaccessioned = sqlalchemy.Column(sqlalchemy.TIMESTAMP, nullable=False,
                                        server_default=sqlalchemy.sql.functions.now())
    timelastmodified = sqlalchemy.Column(sqlalchemy.TIMESTAMP, nullable=False,
                                         server_default=sqlalchemy.sql.functions.now())

    # Constraints
    __tablename__ = "feature"
    __table_args__ = (sqlalchemy.UniqueConstraint(organism_id, uniquename, type_id, name="feature_c1"),
                      sqlalchemy.Index("feature_idx1", dbxref_id),
                      sqlalchemy.Index("feature_idx2", organism_id),
                      sqlalchemy.Index("feature_idx3", type_id),
                      sqlalchemy.Index("feature_idx4", uniquename),
                      sqlalchemy.Index("feature_idx5", sqlalchemy.func.lower(name)))

    # Relationships
    dbxref = sqlalchemy.orm.relationship(general.DbxRef, foreign_keys=dbxref_id, backref="feature_dbxref")
    organism = sqlalchemy.orm.relationship(organism.Organism, foreign_keys=organism_id, backref="feature_organism")
    type = sqlalchemy.orm.relationship(cv.CvTerm, foreign_keys=type_id, backref="feature_type")

    # Initialisation
    def __init__(self, organism_id, type_id, uniquename, dbxref_id=None, name=None, residues=None, seqlen=None,
                 md5checksum=None, is_analysis=False, is_obsolete=False, timeaccessioned=sqlalchemy.sql.functions.now(),
                 timelastmodified=sqlalchemy.sql.functions.now(), feature_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<sequence.Feature(feature_id={0}, dbxref_id={1}, organism_id={2}, name='{3}', uniquename='{4}', " \
               "seqlen={5}, type_id={6}, is_analysis={7}, is_obsolete={8}, timeaccessioned='{9}', " \
               "timelastmodified='{10}')>"\
            .format(self.feature_id, self.dbxref_id, self.organism_id, self.name, self.uniquename, self.seqlen,
                    self.type_id, self.is_analysis, self.is_obsolete, self.timeaccessioned, self.timelastmodified)


class FeatureCvTerm(base.PublicBase):
    """Class for the CHADO 'feature_cvterm' table"""
    # Columns
    feature_cvterm_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    feature_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Feature.feature_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    cvterm_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        cv.CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        pub.Pub.pub_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    is_not = sqlalchemy.Column(sqlalchemy.BOOLEAN, nullable=False, server_default="False")
    rank = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")

    # Constraints
    __tablename__ = "feature_cvterm"
    __table_args__ = (sqlalchemy.UniqueConstraint(feature_id, cvterm_id, pub_id, rank, name="feature_cvterm_c1"),
                      sqlalchemy.Index("feature_cvterm_idx1", feature_id),
                      sqlalchemy.Index("feature_cvterm_idx2", cvterm_id),
                      sqlalchemy.Index("feature_cvterm_idx3", pub_id))

    # Relationships
    feature = sqlalchemy.orm.relationship(Feature, foreign_keys=feature_id, backref="feature_cvterm_feature")
    cvterm = sqlalchemy.orm.relationship(cv.CvTerm, foreign_keys=cvterm_id, backref="feature_cvterm_cvterm")
    pub = sqlalchemy.orm.relationship(pub.Pub, foreign_keys=pub_id, backref="feature_cvterm_pub")

    # Initialisation
    def __init__(self, feature_id, cvterm_id, pub_id, is_not=None, rank=0, feature_cvterm_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<sequence.FeatureCvTerm(feature_cvterm_id={0}, feature_id={1}, cvterm_id={2}, pub_id={3}, is_not={4}, "\
               "rank={5})>".format(self.feature_cvterm_id, self.feature_id, self.cvterm_id, self.pub_id, self.is_not,
                                   self.rank)


class FeatureCvTermDbxRef(base.PublicBase):
    """Class for the CHADO 'feature_cvterm_dbxref' table"""
    # Columns
    feature_cvterm_dbxref_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True,
                                                 autoincrement=True)
    feature_cvterm_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        FeatureCvTerm.feature_cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    dbxref_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        general.DbxRef.dbxref_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    # Constraints
    __tablename__ = "feature_cvterm_dbxref"
    __table_args__ = (sqlalchemy.UniqueConstraint(feature_cvterm_id, dbxref_id, name="feature_cvterm_dbxref_c1"),
                      sqlalchemy.Index("feature_cvterm_dbxref_idx1", feature_cvterm_id),
                      sqlalchemy.Index("feature_cvterm_dbxref_idx2", dbxref_id))

    # Relationships
    feature_cvterm = sqlalchemy.orm.relationship(FeatureCvTerm, foreign_keys=feature_cvterm_id,
                                                 backref="feature_cvterm_dbxref_feature_cvterm")
    dbxref = sqlalchemy.orm.relationship(general.DbxRef, foreign_keys=dbxref_id, backref="feature_cvterm_dbxref_dbxref")

    # Initialisation
    def __init__(self, feature_cvterm_id, dbxref_id, feature_cvterm_dbxref_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<sequence.FeatureCvTermDbxRef(feature_cvterm_dbxref_id={0}, feature_cvterm_id={1}, dbxref_id={2})>".\
            format(self.feature_cvterm_dbxref_id, self.feature_cvterm_id, self.dbxref_id)


class FeatureCvTermProp(base.PublicBase):
    """Class for the CHADO 'feature_cvtermprop' table"""
    # Columns
    feature_cvtermprop_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    feature_cvterm_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        FeatureCvTerm.feature_cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        cv.CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    value = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)
    rank = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")

    # Constraints
    __tablename__ = "feature_cvtermprop"
    __table_args__ = (sqlalchemy.UniqueConstraint(feature_cvterm_id, type_id, rank, name="feature_cvtermprop_c1"),
                      sqlalchemy.Index("feature_cvtermprop_idx1", feature_cvterm_id),
                      sqlalchemy.Index("feature_cvtermprop_idx2", type_id))

    # Relationships
    feature_cvterm = sqlalchemy.orm.relationship(FeatureCvTerm, foreign_keys=feature_cvterm_id,
                                                 backref="feature_cvtermprop_organism")
    type = sqlalchemy.orm.relationship(cv.CvTerm, foreign_keys=type_id, backref="feature_cvtermprop_type")

    # Initialisation
    def __init__(self, feature_cvterm_id, type_id, value=None, rank=0, feature_cvtermprop_id=None):
        for key, val in locals().items():
            if key != self:
                setattr(self, key, val)

    # Representation
    def __repr__(self):
        return "<sequence.FeatureCvTermProp(feature_cvtermprop_id={0}, feature_cvterm_id={1}, type_id={2}, " \
               "value='{3}', rank={4})>".format(self.feature_cvtermprop_id, self.feature_cvterm_id, self.type_id,
                                                self.value, self.rank)


class FeatureCvTermPub(base.PublicBase):
    """Class for the CHADO 'feature_cvterm_pub' table"""
    # Columns
    feature_cvterm_pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    feature_cvterm_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        FeatureCvTerm.feature_cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        pub.Pub.pub_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    # Constraints
    __tablename__ = "feature_cvterm_pub"
    __table_args__ = (sqlalchemy.UniqueConstraint(feature_cvterm_id, pub_id, name="feature_cvterm_pub_c1"),
                      sqlalchemy.Index("feature_cvterm_pub_idx1", feature_cvterm_id),
                      sqlalchemy.Index("feature_cvterm_pub_idx2", pub_id))

    # Relationships
    feature_cvterm = sqlalchemy.orm.relationship(FeatureCvTerm, foreign_keys=feature_cvterm_id,
                                                 backref="feature_cvterm_pub_feature_cvterm")
    pub = sqlalchemy.orm.relationship(pub.Pub, foreign_keys=pub_id, backref="feature_cvterm_pub_pub")

    # Initialisation
    def __init__(self, feature_cvterm_id, pub_id, feature_cvterm_pub_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<sequence.FeatureCvTermPub(feature_cvterm_pub_id={0}, feature_cvterm_id={1}, pub_id={2})>".\
            format(self.feature_cvterm_pub_id, self.feature_cvterm_id, self.pub_id)


class FeatureDbxRef(base.PublicBase):
    """Class for the CHADO 'feature_dbxref' table"""
    # Columns
    feature_dbxref_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    feature_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Feature.feature_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    dbxref_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        general.DbxRef.dbxref_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    is_current = sqlalchemy.Column(sqlalchemy.BOOLEAN, nullable=False, server_default="True")

    # Constraints
    __tablename__ = "feature_dbxref"
    __table_args__ = (sqlalchemy.UniqueConstraint(feature_id, dbxref_id, name="feature_dbxref_c1"),
                      sqlalchemy.Index("feature_dbxref_idx1", feature_id),
                      sqlalchemy.Index("feature_dbxref_idx2", dbxref_id))

    # Relationships
    feature = sqlalchemy.orm.relationship(Feature, foreign_keys=feature_id, backref="feature_dbxref_feature")
    dbxref = sqlalchemy.orm.relationship(general.DbxRef, foreign_keys=dbxref_id, backref="feature_dbxref_dbxref")

    # Initialisation
    def __init__(self, feature_id, dbxref_id, is_current=True, feature_dbxref_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<sequence.FeatureDbxRef(feature_dbxref_id={0}, feature_id={1}, dbxref_id={2}, is_current={3})>".\
            format(self.feature_dbxref_id, self.feature_id, self.dbxref_id, self.is_current)


class FeaturePub(base.PublicBase):
    """Class for the CHADO 'feature_pub' table"""
    # Columns
    feature_pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    feature_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Feature.feature_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        pub.Pub.pub_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    # Constraints
    __tablename__ = "feature_pub"
    __table_args__ = (sqlalchemy.UniqueConstraint(feature_id, pub_id, name="feature_pub_c1"),
                      sqlalchemy.Index("feature_pub_idx1", feature_id),
                      sqlalchemy.Index("feature_pub_idx2", pub_id))

    # Relationships
    feature = sqlalchemy.orm.relationship(Feature, foreign_keys=feature_id, backref="feature_pub_feature")
    pub = sqlalchemy.orm.relationship(pub.Pub, foreign_keys=pub_id, backref="feature_pub_pub")

    # Initialisation
    def __init__(self, feature_id, pub_id, feature_pub_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<sequence.FeaturePub(feature_pub_id={0}, feature_id={1}, pub_id={2})>". \
            format(self.feature_pub_id, self.feature_id, self.pub_id)


class FeaturePubProp(base.PublicBase):
    """Class for the CHADO 'feature_pubprop' table"""
    # Columns
    feature_pubprop_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    feature_pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        FeaturePub.feature_pub_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        cv.CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    value = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)
    rank = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")

    # Constraints
    __tablename__ = "feature_pubprop"
    __table_args__ = (sqlalchemy.UniqueConstraint(feature_pub_id, type_id, rank, name="feature_pubprop_c1"),
                      sqlalchemy.Index("feature_pubprop_idx1", feature_pub_id),
                      sqlalchemy.Index("feature_pubprop_idx2", type_id))

    # Relationships
    feature_pub = sqlalchemy.orm.relationship(FeaturePub, foreign_keys=feature_pub_id,
                                              backref="feature_pubprop_feature_pub")
    type = sqlalchemy.orm.relationship(cv.CvTerm, foreign_keys=type_id, backref="feature_pubprop_type")

    # Initialisation
    def __init__(self, feature_pub_id, type_id, value=None, rank=0, feature_pubprop_id=None):
        for key, val in locals().items():
            if key != self:
                setattr(self, key, val)

    # Representation
    def __repr__(self):
        return "<sequence.FeaturePubProp(feature_pubprop_id={0}, feature_pub_id={1}, type_id={2}, value='{3}', " \
               "rank={4})>".format(self.feature_pubprop_id, self.feature_pub_id, self.type_id, self.value, self.rank)


class FeatureRelationship(base.PublicBase):
    """Class for the CHADO 'feature_relationship' table"""
    # Columns
    feature_relationship_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    subject_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Feature.feature_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    object_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Feature.feature_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        cv.CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    value = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)
    rank = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")

    # Constraints
    __tablename__ = "feature_relationship"
    __table_args__ = (sqlalchemy.UniqueConstraint(subject_id, object_id, type_id, rank, name="feature_relationship_c1"),
                      sqlalchemy.Index("feature_relationship_idx1", subject_id),
                      sqlalchemy.Index("feature_relationship_idx2", object_id),
                      sqlalchemy.Index("feature_relationship_idx3", type_id))

    # Relationships
    type = sqlalchemy.orm.relationship(cv.CvTerm, foreign_keys=type_id, backref="feature_relationship_type")
    subject = sqlalchemy.orm.relationship(Feature, foreign_keys=subject_id, backref="feature_relationship_subject")
    object = sqlalchemy.orm.relationship(Feature, foreign_keys=object_id, backref="feature_relationship_object")

    # Initialisation
    def __init__(self, subject_id, object_id, type_id, value=None, rank=0, feature_relationship_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<sequence.FeatureRelationship(feature_relationship_id={0}, subject_id={1}, object_id={2}, " \
               "type_id={3}, value='{4}', rank={5})>".format(self.feature_relationship_id, self.subject_id,
                                                             self.object_id, self.type_id, self.value, self.rank)


class FeatureRelationshipPub(base.PublicBase):
    """Class for the CHADO 'feature_relationship_pub' table"""
    # Columns
    feature_relationship_pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True,
                                                    autoincrement=True)
    feature_relationship_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        FeatureRelationship.feature_relationship_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        pub.Pub.pub_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    # Constraints
    __tablename__ = "feature_relationship_pub"
    __table_args__ = (sqlalchemy.UniqueConstraint(feature_relationship_id, pub_id, name="feature_relationship_pub_c1"),
                      sqlalchemy.Index("feature_relationship_pub_idx1", feature_relationship_id),
                      sqlalchemy.Index("feature_relationship_pub_idx2", pub_id))

    # Relationships
    feature_relationship = sqlalchemy.orm.relationship(FeatureRelationship, foreign_keys=feature_relationship_id,
                                                       backref="feature_relationship_pub_feature_relationship")
    pub = sqlalchemy.orm.relationship(pub.Pub, foreign_keys=pub_id, backref="feature_relationship_pub_pub")

    # Initialisation
    def __init__(self, feature_relationship_id, pub_id, feature_relationship_pub_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<sequence.FeatureRelationshipPub(feature_relationship_pub_id={0}, feature_relationship_id={1}, " \
               "pub_id={2})>".format(self.feature_relationship_pub_id, self.feature_relationship_id, self.pub_id)


class FeatureRelationshipProp(base.PublicBase):
    """Class for the CHADO 'feature_relationshipprop' table"""
    # Columns
    feature_relationshipprop_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True,
                                                    autoincrement=True)
    feature_relationship_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        FeatureRelationship.feature_relationship_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        cv.CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    value = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)
    rank = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")

    # Constraints
    __tablename__ = "feature_relationshipprop"
    __table_args__ = (sqlalchemy.UniqueConstraint(feature_relationship_id, type_id, rank,
                                                  name="feature_relationshipprop_c1"),
                      sqlalchemy.Index("feature_relationshipprop_idx1", feature_relationship_id),
                      sqlalchemy.Index("feature_relationshipprop_idx2", type_id))

    # Relationships
    feature_relationship = sqlalchemy.orm.relationship(FeatureRelationship, foreign_keys=feature_relationship_id,
                                                       backref="feature_relationshipprop_feature_relationship")
    type = sqlalchemy.orm.relationship(cv.CvTerm, foreign_keys=type_id, backref="feature_relationshipprop_type")

    # Initialisation
    def __init__(self, feature_relationship_id, type_id, value=None, rank=0, feature_relationshipprop_id=None):
        for key, val in locals().items():
            if key != self:
                setattr(self, key, val)

    # Representation
    def __repr__(self):
        return "<sequence.FeatureRelationshipProp(feature_relationshipprop_id={0}, feature_relationship_id={1}, " \
               "type_id={2}, value='{3}', rank={4})>".\
            format(self.feature_relationshipprop_id, self.feature_relationship_id, self.type_id, self.value, self.rank)


class FeatureRelationshipPropPub(base.PublicBase):
    """Class for the CHADO 'feature_relationshipprop_pub' table"""
    # Columns
    feature_relationshipprop_pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True,
                                                        autoincrement=True)
    feature_relationshipprop_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        FeatureRelationshipProp.feature_relationshipprop_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        pub.Pub.pub_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    # Constraints
    __tablename__ = "feature_relationshipprop_pub"
    __table_args__ = (sqlalchemy.UniqueConstraint(feature_relationshipprop_id, pub_id,
                                                  name="feature_relationshipprop_pub_c1"),
                      sqlalchemy.Index("feature_relationshipprop_pub_idx1", feature_relationshipprop_id),
                      sqlalchemy.Index("feature_relationshipprop_pub_idx2", pub_id))

    # Relationships
    feature_relationshipprop = sqlalchemy.orm.relationship(
        FeatureRelationshipProp, foreign_keys=feature_relationshipprop_id,
        backref="feature_relationshipprop_pub_feature_relationshipprop")
    pub = sqlalchemy.orm.relationship(pub.Pub, foreign_keys=pub_id, backref="feature_relationshipprop_pub_pub")

    # Initialisation
    def __init__(self, feature_relationshipprop_id, pub_id, feature_relationshipprop_pub_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<sequence.FeatureRelationshipPropPub(feature_relationshipprop_pub_id={0}, " \
               "feature_relationshipprop_id={1}, pub_id={2})>".\
            format(self.feature_relationshipprop_pub_id, self.feature_relationshipprop_id, self.pub_id)


class Synonym(base.PublicBase):
    """Class for the CHADO 'synonym' table"""
    # Columns
    synonym_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=False)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        cv.CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    synonym_sgml = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=False)

    # Constraints
    __tablename__ = "synonym"
    __table_args__ = (sqlalchemy.UniqueConstraint(name, type_id, name="synonym_c1"),
                      sqlalchemy.Index("synonym_idx1", type_id),
                      sqlalchemy.Index("synonym_idx2", sqlalchemy.func.lower(synonym_sgml)))

    # Relationships
    type = sqlalchemy.orm.relationship(cv.CvTerm, foreign_keys=type_id, backref="synonym_type")

    # Initialisation
    def __init__(self, name, type_id, synonym_sgml, synonym_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<sequence.Synonym(synonym_id={0}, name='{1}', type_id={2}, synonym_sgml='{3}')>".\
            format(self.synonym_id, self.name, self.type_id, self.synonym_sgml)


class FeatureSynonym(base.PublicBase):
    """Class for the CHADO 'feature_synonym' table"""
    # Columns
    feature_synonym_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    synonym_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Synonym.synonym_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    feature_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Feature.feature_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        pub.Pub.pub_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    is_current = sqlalchemy.Column(sqlalchemy.BOOLEAN, nullable=False, server_default="True")
    is_internal = sqlalchemy.Column(sqlalchemy.BOOLEAN, nullable=False, server_default="False")

    # Constraints
    __tablename__ = "feature_synonym"
    __table_args__ = (sqlalchemy.UniqueConstraint(synonym_id, feature_id, pub_id, name="feature_synonym_c1"),
                      sqlalchemy.Index("feature_synonym_idx1", synonym_id),
                      sqlalchemy.Index("feature_synonym_idx2", feature_id),
                      sqlalchemy.Index("feature_synonym_idx3", pub_id))

    # Relationships
    synonym = sqlalchemy.orm.relationship(Synonym, foreign_keys=synonym_id, backref="feature_synonym_synonym")
    feature = sqlalchemy.orm.relationship(Feature, foreign_keys=feature_id, backref="feature_synonym_feature")
    pub = sqlalchemy.orm.relationship(pub.Pub, foreign_keys=pub_id, backref="feature_synonym_pub")

    # Initialisation
    def __init__(self, synonym_id, feature_id, pub_id, is_current=None, is_internal=None, feature_synonym_id=None):
        for key, val in locals().items():
            if key != self:
                setattr(self, key, val)

    # Representation
    def __repr__(self):
        return "<sequence.FeatureSynonym(feature_synonym_id={0}, synonym_id={1}, feature_id={2}, pub_id={3}, " \
               "is_current={4}, is_internal={5})>".format(self.feature_synonym_id, self.synonym_id, self.feature_id,
                                                          self.pub_id, self.is_current, self.is_internal)


class FeatureLoc(base.PublicBase):
    """Class for the CHADO 'featureloc' table"""
    # Columns
    featureloc_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    feature_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Feature.feature_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    srcfeature_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Feature.feature_id, onupdate="CASCADE", ondelete="SET NULL"), nullable=True)
    fmin = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=True)
    is_fmin_partial = sqlalchemy.Column(sqlalchemy.BOOLEAN, nullable=False, server_default="False")
    fmax = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=True)
    is_fmax_partial = sqlalchemy.Column(sqlalchemy.BOOLEAN, nullable=False, server_default="False")
    strand = sqlalchemy.Column(sqlalchemy.SMALLINT, nullable=True)
    phase = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=True)
    residue_info = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)
    locgroup = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")
    rank = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")

    # Constraints
    __tablename__ = "featureloc"
    __table_args__ = (sqlalchemy.UniqueConstraint(feature_id, locgroup, rank, name="featureloc_c1"),
                      sqlalchemy.CheckConstraint("fmin <= fmax", name="featureloc_c2"),
                      sqlalchemy.Index("featureloc_idx1", feature_id),
                      sqlalchemy.Index("featureloc_idx2", srcfeature_id),
                      sqlalchemy.Index("featureloc_idx3", srcfeature_id, fmin, fmax))

    # Relationships
    feature = sqlalchemy.orm.relationship(Feature, foreign_keys=feature_id, backref="featureloc_feature")
    srcfeature = sqlalchemy.orm.relationship(Feature, foreign_keys=srcfeature_id, backref="featureloc_srcfeature")

    # Initialisation
    def __init__(self, feature_id, srcfeature_id, fmin=None, is_fmin_partial=False, fmax=None, is_fmax_partial=False,
                 strand=None, phase=None, residue_info=None, locgroup=0, rank=0, featureloc_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<sequence.FeatureLoc(featureloc_id={0}, feature_id={1}, srcfeature_id={2}, fmin={3}, " \
               "is_fmin_partial={4}, fmax={5}, is_fmax_partial={6}, strand={7}, phase={8}, residue_info='{9}', " \
               "locgroup={10}, rank={11})>".format(self.featureloc_id, self.feature_id, self.srcfeature_id, self.fmin,
                                                   self.is_fmin_partial, self.fmax, self.is_fmax_partial, self.strand,
                                                   self.phase, self.residue_info, self.locgroup, self.rank)


class FeatureLocPub(base.PublicBase):
    """Class for the CHADO 'featureloc_pub' table"""
    # Columns
    featureloc_pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    featureloc_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        FeatureLoc.featureloc_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        pub.Pub.pub_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    # Constraints
    __tablename__ = "featureloc_pub"
    __table_args__ = (sqlalchemy.UniqueConstraint(featureloc_id, pub_id, name="featureloc_pub_c1"),
                      sqlalchemy.Index("featureloc_pub_idx1", featureloc_id),
                      sqlalchemy.Index("featureloc_pub_idx2", pub_id))

    # Relationships
    featureloc = sqlalchemy.orm.relationship(FeatureLoc, foreign_keys=featureloc_id,
                                             backref="featureloc_pub_featureloc")
    pub = sqlalchemy.orm.relationship(pub.Pub, foreign_keys=pub_id, backref="featureloc_pub_pub")

    # Initialisation
    def __init__(self, featureloc_id, pub_id, featureloc_pub_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<sequence.FeatureLocPub(featureloc_pub_id={0}, featureloc_id={1}, pub_id={2})>".\
            format(self.featureloc_pub_id, self.featureloc_id, self.pub_id)


class FeatureProp(base.PublicBase):
    """Class for the CHADO 'featureprop' table"""
    # Columns
    featureprop_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    feature_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Feature.feature_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        cv.CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    value = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)
    rank = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")

    # Constraints
    __tablename__ = "featureprop"
    __table_args__ = (sqlalchemy.UniqueConstraint(feature_id, type_id, rank, name="featureprop_c1"),
                      sqlalchemy.Index("featureprop_idx1", feature_id),
                      sqlalchemy.Index("featureprop_idx2", type_id))

    # Relationships
    feature = sqlalchemy.orm.relationship(Feature, foreign_keys=feature_id, backref="featureprop_feature")
    type = sqlalchemy.orm.relationship(cv.CvTerm, foreign_keys=type_id, backref="featureprop_type")

    # Initialisation
    def __init__(self, feature_id, type_id, value=None, rank=0, featureprop_id=None):
        for key, val in locals().items():
            if key != self:
                setattr(self, key, val)

    # Representation
    def __repr__(self):
        return "<sequence.FeatureProp(featureprop_id={0}, feature_id={1}, type_id={2}, value='{3}', rank={4})>". \
            format(self.featureprop_id, self.feature_id, self.type_id, self.value, self.rank)


class FeaturePropPub(base.PublicBase):
    """Class for the CHADO 'featureprop_pub' table"""
    # Columns
    featureprop_pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    featureprop_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        FeatureProp.featureprop_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    pub_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        pub.Pub.pub_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    # Constraints
    __tablename__ = "featureprop_pub"
    __table_args__ = (sqlalchemy.UniqueConstraint(featureprop_id, pub_id, name="featureprop_pub_c1"),
                      sqlalchemy.Index("featureprop_pub_idx1", featureprop_id),
                      sqlalchemy.Index("featureprop_pub_idx2", pub_id))

    # Relationships
    featureprop = sqlalchemy.orm.relationship(FeatureProp, foreign_keys=featureprop_id,
                                              backref="featureprop_pub_featureprop")
    pub = sqlalchemy.orm.relationship(pub.Pub, foreign_keys=pub_id, backref="featureprop_pub_pub")

    # Initialisation
    def __init__(self, featureprop_id, pub_id, featureprop_pub_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<sequence.FeaturePropPub(featureprop_pub_id={0}, featureprop_id={1}, pub_id={2})>".\
            format(self.featureprop_pub_id, self.featureprop_id, self.pub_id)
