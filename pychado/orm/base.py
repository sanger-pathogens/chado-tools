import sqlalchemy.ext.declarative

# Supplies the base for declarative mappings
Base: sqlalchemy.MetaData = sqlalchemy.ext.declarative.declarative_base()
