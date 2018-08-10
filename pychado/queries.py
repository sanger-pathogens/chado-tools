import pkg_resources
from pychado import utils


def load_list_query(specifier: str, arguments) -> str:
    """Loads the SQL query for a 'chado list' command"""
    query = ""
    if specifier == "organisms":
        query = utils.read_text(pkg_resources.resource_filename("pychado", "sql/list_organisms.sql"))
    elif specifier == "products":
        template = utils.read_text(pkg_resources.resource_filename("pychado", "sql/list_products.sql"))
        query = set_organism_condition(template, arguments)
    return query


def load_stats_query(specifier: str, arguments) -> str:
    """Loads the SQL query for a 'chado stats' command"""
    query = ""
    if specifier == "annotations":
        template = utils.read_text(pkg_resources.resource_filename("pychado", "sql/stats_annotations.sql"))
        query = set_organism_condition(template, arguments)
    elif specifier == "eupathdb_tags":
        template = utils.read_text(pkg_resources.resource_filename("pychado", "sql/stats_eupath.sql"))
        query = set_organism_condition(template, arguments)
    return query


def load_insert_statement(specifier: str) -> str:
    """Loads the SQL statement for a 'chado insert' command"""
    statement = ""
    if specifier == "organism":
        statement = utils.read_text(pkg_resources.resource_filename("pychado", "sql/insert_organism.sql"))
    return statement


def load_delete_statement(specifier: str, arguments) -> str:
    """Loads the SQL statement for a 'chado delete' command"""
    statement = ""
    if specifier == "organism":
        template = utils.read_text(pkg_resources.resource_filename("pychado", "sql/delete_organism.sql"))
        statement = set_organism_condition(template, arguments)
    return statement


def set_organism_condition(query: str, arguments) -> str:
    """Replaces a placeholder in a query with a condition restricting results to certain organisms"""
    if not hasattr(arguments, "abbreviation") or arguments.abbreviation == "all":
        modified_query = query.replace('{{CONDITION}}', 'TRUE')
    else:
        condition = utils.read_text(pkg_resources.resource_filename("pychado", "sql/condition_organism.sql"))
        modified_query = query.replace('{{CONDITION}}', condition)
    return modified_query


def specify_list_parameters(specifier: str, arguments) -> tuple:
    """Specifies the parameters that complete the SQL query of a 'chado list' command"""
    if specifier == "products":
        if arguments.abbreviation != "all":
            params = (arguments.abbreviation, )
        else:
            params = tuple()
    else:
        params = tuple()
    return params


def specify_stats_parameters(arguments) -> tuple:
    """Specifies the parameters that complete the SQL query of a 'chado stats' command"""
    if arguments.abbreviation != "all":
        params = (arguments.date, arguments.abbreviation)
    else:
        params = (arguments.date,)
    return params


def specify_insert_parameters(specifier: str, arguments) -> tuple:
    """Specifies the parameters that complete the SQL query of a 'chado insert' command"""
    if specifier == "organism":
        if not arguments.common_name:
            arguments.common_name = arguments.abbreviation
        params = (arguments.genus, arguments.species, arguments.abbreviation, arguments.common_name, arguments.comment)
    else:
        params = tuple()
    return params


def specify_delete_parameters(specifier: str, arguments) -> tuple:
    """Specifies the parameters that complete the SQL query of a 'chado delete' command"""
    if specifier == "organism":
        params = (arguments.abbreviation, )
    else:
        params = tuple()
    return params


def load_maximum_id_query(specifier: str) -> str:
    """Loads the SQL query that determines the maximum ID of a given table in a CHADO database"""
    query = ""
    if specifier == "organism":
        query = utils.read_text(pkg_resources.resource_filename("pychado", "sql/max_organism_id.sql"))
    return query
