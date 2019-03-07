import sqlalchemy.orm
import sqlalchemy.sql.functions
from . import base, cv, sequence

# Object-relational mappings for the CHADO Companalysis module


class Analysis(base.PublicBase):
    """Class for the CHADO 'analysis' table"""
    # Columns
    analysis_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    description = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)
    program = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=False)
    programversion = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=False)
    algorithm = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    sourcename = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    sourceversion = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    sourceuri = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)
    timeexecuted = sqlalchemy.Column(sqlalchemy.TIMESTAMP, nullable=False,
                                     server_default=sqlalchemy.sql.functions.now())

    # Constraints
    __tablename__ = "analysis"
    __table_args__ = (sqlalchemy.UniqueConstraint(program, programversion, sourcename, name="analysis_c1"),)

    # Initialisation
    def __init__(self, program, programversion, name=None, description=None, algorithm=None, sourcename=None,
                 sourceversion=None, sourceuri=None, timeexecuted=sqlalchemy.sql.functions.now(), analysis_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<companalysis.Analysis(analysis_id={0}, name='{1}', desription='{2}', program='{3}', " \
               "programversion='{4}', algorithm='{5}', sourcename='{6}', sourceversion='{7}, sourceuri='{8}'," \
               "timeexecuted='{9}')>".format(self.analysis_id, self.name, self.description, self.program,
                                             self.programversion, self.algorithm, self.sourcename, self.sourceversion,
                                             self.sourceuri, self.timeexecuted)


class AnalysisFeature(base.PublicBase):
    """Class for the CHADO 'analysisfeature' table"""
    # Columns
    analysisfeature_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    feature_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        sequence.Feature.feature_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    analysis_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Analysis.analysis_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    rawscore = sqlalchemy.Column(sqlalchemy.FLOAT, nullable=True)
    normscore = sqlalchemy.Column(sqlalchemy.FLOAT, nullable=True)
    significance = sqlalchemy.Column(sqlalchemy.FLOAT, nullable=True)
    identity = sqlalchemy.Column(sqlalchemy.FLOAT, nullable=True)

    # Constraints
    __tablename__ = "analysisfeature"
    __table_args__ = (sqlalchemy.UniqueConstraint(feature_id, analysis_id, name="analysisfeature_c1"),
                      sqlalchemy.Index("analysisfeature_idx1", feature_id),
                      sqlalchemy.Index("analysisfeature_idx2", analysis_id))

    # Relationships
    feature = sqlalchemy.orm.relationship(sequence.Feature, foreign_keys=feature_id, backref="analysisfeature_feature")
    analysis = sqlalchemy.orm.relationship(Analysis, foreign_keys=analysis_id, backref="analysisfeature_analysis")

    # Initialisation
    def __init__(self, feature_id, analysis_id, rawscore=None, normscore=None, significance=None, identity=None,
                 analysisfeature_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<companalysis.AnalysisFeature(analysisfeature_id={0}, feature_id={1}, analysis_id={2}, rawscore={3}, " \
               "normscore={4}, significance={5}, identity={6})>".\
            format(self.analysisfeature_id, self.feature_id, self.analysis_id, self.rawscore, self.normscore,
                   self.significance, self.identity)


class AnalysisProp(base.PublicBase):
    """Class for the CHADO 'analysisprop' table"""
    # Columns
    analysisprop_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    analysis_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Analysis.analysis_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        cv.CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    value = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)

    # Constraints
    __tablename__ = "analysisprop"
    __table_args__ = (sqlalchemy.UniqueConstraint(analysis_id, type_id, value, name="analysisprop_c1"),
                      sqlalchemy.Index("analysisprop_idx1", analysis_id),
                      sqlalchemy.Index("analysisprop_idx2", type_id))

    # Relationships
    analysis = sqlalchemy.orm.relationship(Analysis, foreign_keys=analysis_id, backref="analysisprop_analysis")
    type = sqlalchemy.orm.relationship(cv.CvTerm, foreign_keys=type_id, backref="analysisprop_type")

    # Initialisation
    def __init__(self, analysis_id, type_id, value=None, analysisprop_id=None):
        for key, val in locals().items():
            if key != self:
                setattr(self, key, val)

    # Representation
    def __repr__(self):
        return "<companalysis.AnalysisProp(analysisprop_id={0}, analysis_id={1}, type_id={2}, value='{3}')>". \
            format(self.analysisprop_id, self.analysis_id, self.type_id, self.value)
