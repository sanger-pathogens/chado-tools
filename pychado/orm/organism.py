import sqlalchemy.orm
from pychado.orm.base import Base
from pychado.orm.cv import CvTerm

# Object-relational mappings for the CHADO Organism module


class Organism(Base):
    """Class for the CHADO 'organism' table"""
    # Columns
    organism_id = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, primary_key=True, autoincrement=True)
    abbreviation = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    genus = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=False)
    species = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=False)
    common_name = sqlalchemy.Column(sqlalchemy.VARCHAR(255), nullable=True)
    infraspecific_name = sqlalchemy.Column(sqlalchemy.VARCHAR(1024), nullable=True)
    type_id = sqlalchemy.Column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey(
        CvTerm.cvterm_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=True)
    comment = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)

    # Constraints
    __tablename__ = "organism"
    __table_args__ = (sqlalchemy.UniqueConstraint(genus, species, type_id, infraspecific_name, name="organism_c1"), )

    # Relationships
    type = sqlalchemy.orm.relationship(CvTerm, foreign_keys=type_id, backref="organism_type")

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
