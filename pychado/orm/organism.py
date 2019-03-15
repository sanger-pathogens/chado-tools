import sqlalchemy.orm
from . import base, general, cv


# Object-relational mappings for the CHADO Organism module


class Organism(base.PublicBase):
    """Class for the CHADO 'organism' table"""
    # Columns
    organism_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    abbreviation = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=False)
    genus = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=False)
    species = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=False)
    common_name = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    infraspecific_name = sqlalchemy.Column(sqlalchemy.VARCHAR(1024), nullable=True)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        cv.CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=True)
    comment = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)

    # Constraints
    __tablename__ = "organism"
    __table_args__ = (sqlalchemy.UniqueConstraint(genus, species, infraspecific_name, name="organism_c1"),
                      sqlalchemy.UniqueConstraint(abbreviation, name="organism_c2"))

    # Relationships
    type = sqlalchemy.orm.relationship(cv.CvTerm, foreign_keys=type_id, backref="organism_type")

    # Initialisation
    def __init__(self, genus, species, abbreviation=None, common_name=None, infraspecific_name=None,
                 type_id=None, comment=None, organism_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<organism.Organism(organism_id={0}, abbreviation='{1}', genus='{2}', species='{3}', " \
               "common_name='{4}', infraspecific_name='{5}', type_id={6}, comment='{7}')>"\
            .format(self.organism_id, self.abbreviation, self.genus, self.species, self.common_name,
                    self.infraspecific_name, self.type_id, self.comment)


class OrganismDbxRef(base.PublicBase):
    """Class for the CHADO 'organism_dbxref' table"""
    # Columns
    organism_dbxref_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    organism_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Organism.organism_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    dbxref_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        general.DbxRef.dbxref_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    # Constraints
    __tablename__ = "organism_dbxref"
    __table_args__ = (sqlalchemy.UniqueConstraint(organism_id, dbxref_id, name="organism_dbxref_c1"),
                      sqlalchemy.Index("organism_dbxref_idx1", organism_id),
                      sqlalchemy.Index("organism_dbxref_idx2", dbxref_id))

    # Relationships
    organism = sqlalchemy.orm.relationship(Organism, foreign_keys=organism_id, backref=sqlalchemy.orm.backref(
        "organism_dbxref_organism", passive_deletes=True))
    dbxref = sqlalchemy.orm.relationship(general.DbxRef, backref="organism_dbxref_dbxref")

    # Initialisation
    def __init__(self, organism_id, dbxref_id, organism_dbxref_id=None):
        for key, value in locals().items():
            if key != self:
                setattr(self, key, value)

    # Representation
    def __repr__(self):
        return "<organism.OrganismDbxRef(organism_dbxref_id={0}, organism_id={1}, dbxref_id={2})>".format(
            self.organism_dbxref_id, self.organism_id, self.dbxref_id)


class OrganismProp(base.PublicBase):
    """Class for the CHADO 'organismprop' table"""
    # Columns
    organismprop_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    organism_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        Organism.organism_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        cv.CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    value = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)
    rank = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False, server_default="0")

    # Constraints
    __tablename__ = "organismprop"
    __table_args__ = (sqlalchemy.UniqueConstraint(organism_id, type_id, rank, name="organismprop_c1"),
                      sqlalchemy.Index("organismprop_idx1", organism_id),
                      sqlalchemy.Index("organismprop_idx2", type_id))

    # Relationships
    organism = sqlalchemy.orm.relationship(Organism, foreign_keys=organism_id, backref=sqlalchemy.orm.backref(
        "organismprop_organism", passive_deletes=True))
    type = sqlalchemy.orm.relationship(cv.CvTerm, foreign_keys=type_id, backref="organismprop_type")

    # Initialisation
    def __init__(self, organism_id, type_id, value=None, rank=0, organismprop_id=None):
        for key, val in locals().items():
            if key != self:
                setattr(self, key, val)

    # Representation
    def __repr__(self):
        return "<organism.OrganismProp(organismprop_id={0}, organism_id={1}, type_id={2}, value='{3}', rank={4})>"\
            .format(self.organismprop_id, self.organism_id, self.type_id, self.value, self.rank)
