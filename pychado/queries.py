import pkg_resources
import sqlalchemy.sql.expression
from . import utils


def load_query(specifier: str) -> str:
    """Loads the SQL query for a 'chado extract' command"""
    query = ""
    if specifier == "public_organisms":
        query = utils.read_text(pkg_resources.resource_filename("pychado", "sql/extract_public_organisms.sql"))
    elif specifier == "organisms":
        query = utils.read_text(pkg_resources.resource_filename("pychado", "sql/extract_organisms.sql"))
    elif specifier == "cvterms":
        query = utils.read_text(pkg_resources.resource_filename("pychado", "sql/extract_cvterms.sql"))
    elif specifier == "public_gene_products":
        query = utils.read_text(pkg_resources.resource_filename("pychado", "sql/extract_public_gene_products.sql"))
    elif specifier == "gene_products":
        query = utils.read_text(pkg_resources.resource_filename("pychado", "sql/extract_gene_products.sql"))
    elif specifier == "public_annotation_updates":
        query = utils.read_text(pkg_resources.resource_filename("pychado", "sql/extract_public_annotation_updates.sql"))
    elif specifier == "annotation_updates":
        query = utils.read_text(pkg_resources.resource_filename("pychado", "sql/extract_annotation_updates.sql"))
    elif specifier == "public_curator_comments":
        query = utils.read_text(pkg_resources.resource_filename("pychado", "sql/extract_public_curator_comments.sql"))
    elif specifier == "curator_comments":
        query = utils.read_text(pkg_resources.resource_filename("pychado", "sql/extract_curator_comments.sql"))
    return query


def set_query_conditions(query: str, **kwargs) -> sqlalchemy.sql.expression.TextClause:
    """Replaces placeholder in a query and binds parameters"""

    # Set/remove conditions in WHERE clause
    if "organism" in kwargs.keys():
        query = set_organism_condition(query, kwargs["organism"])
    if "database" in kwargs.keys():
        query = set_database_condition(query, kwargs["database"])
    if "vocabulary" in kwargs.keys():
        query = set_vocabulary_condition(query, kwargs["vocabulary"])

    # Bind parameters
    final_query = bind_parameters(query, **kwargs)
    return final_query


def bind_parameters(query: str, **kwargs) -> sqlalchemy.sql.expression.TextClause:
    """Binds parameters to a given query"""
    text_query = sqlalchemy.text(query)
    for key, value in kwargs.items():
        if value:
            text_query = text_query.bindparams(sqlalchemy.bindparam(key, value=value))
    return text_query


def set_organism_condition(query: str, organism: str) -> str:
    """Replaces a placeholder in a query with a condition restricting results to a certain organism"""
    if not organism:
        modified_query = query.replace(":ORGANISM_CONDITION", "TRUE")
    else:
        modified_query = query.replace(":ORGANISM_CONDITION", "abbreviation = :organism")
    return modified_query


def set_database_condition(query: str, database: str) -> str:
    """Replaces a placeholder in a query with a condition restricting results to a certain database"""
    if not database:
        modified_query = query.replace(":DB_CONDITION", "TRUE")
    else:
        modified_query = query.replace(":DB_CONDITION", "db.name = :database")
    return modified_query


def set_vocabulary_condition(query: str, vocabulary: str) -> str:
    """Replaces a placeholder in a query with a condition restricting results to a certain vocabulary"""
    if not vocabulary:
        modified_query = query.replace(":CV_CONDITION", "TRUE")
    else:
        modified_query = query.replace(":CV_CONDITION", "cv.name = :vocabulary")
    return modified_query
