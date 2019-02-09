import sqlalchemy.ext.declarative

# Supplies the base for declarative mappings
PublicBase = sqlalchemy.ext.declarative.declarative_base(metadata=sqlalchemy.schema.MetaData(schema='public'))
AuditBase = sqlalchemy.ext.declarative.declarative_base(metadata=sqlalchemy.schema.MetaData(schema='audit'))

# Define data types
BIGINT = sqlalchemy.BIGINT().with_variant(sqlalchemy.INTEGER(), 'sqlite')
operation_type = sqlalchemy.Enum('INSERT', 'UPDATE', 'DELETE', 'BEFORE', name='operation_type')
