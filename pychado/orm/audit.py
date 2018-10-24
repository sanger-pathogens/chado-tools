import sqlalchemy.sql.functions
from . import base

# Object-relational mappings for the CHADO 'audit' module
# Note: the 'type' column can alternatively be defined as CHAR with additional CHECK constraint.
# If doing so, the check constraint must also be transferred to the child tables (created automatically in ddl.py).
# SQLAlchemy currently doesn't support retrieving CHECK constraints from TABLE objects -> use __table_args__


class Audit(base.AuditBase):
    """Parent class for tables in the CHADO 'audit' schema"""

    # Sequences
    audit_sequence = sqlalchemy.Sequence('audit_id_seq', metadata=base.AuditBase.metadata)

    # Columns
    audit_id = sqlalchemy.Column(sqlalchemy.BIGINT, audit_sequence, nullable=False,
                                 server_default=audit_sequence.next_value(), primary_key=True)
    type = sqlalchemy.Column(base.operation_type, nullable=False)
    # type = sqlalchemy.Column('type', sqlalchemy.CHAR(6), nullable=False)
    username = sqlalchemy.Column(sqlalchemy.TEXT, nullable=False,
                                 server_default=sqlalchemy.sql.functions.current_user())
    time = sqlalchemy.Column(sqlalchemy.TIMESTAMP, nullable=False,
                             server_default=sqlalchemy.sql.functions.current_timestamp())

    # Constraints
    __tablename__ = "audit"
    # __table_args__ = (sqlalchemy.CheckConstraint("type IN ('INSERT', 'UPDATE', 'DELETE')", name="audit_type_check"), )
