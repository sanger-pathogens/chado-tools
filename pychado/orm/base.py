import sqlalchemy.ext.declarative

# Supplies the base for declarative mappings
Base: sqlalchemy.schema.MetaData = sqlalchemy.ext.declarative.declarative_base()

BIGINT = sqlalchemy.BIGINT().with_variant(sqlalchemy.INTEGER(), 'sqlite')
