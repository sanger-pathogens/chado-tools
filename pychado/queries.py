import pkg_resources
from pychado import utils


def load_list_query(specifier: str, arguments) -> str:
    """Loads the SQL query for a 'chado list' command"""
    query = ""
    if specifier == "organisms":
        query = utils.read_text(pkg_resources.resource_filename("pychado", "sql/list_organisms.sql"))
    elif specifier == "cvterms":
        template = utils.read_text(pkg_resources.resource_filename("pychado", "sql/list_cvterms.sql"))
        template = set_vocabulary_condition(template, arguments)
        query = set_database_condition(template, arguments)
    elif specifier == "genedb_products":
        template = utils.read_text(pkg_resources.resource_filename("pychado", "sql/list_genedb_products.sql"))
        query = set_organism_condition(template, arguments)
    return query


def load_stats_query(arguments) -> str:
    """Loads the SQL query for a 'chado stats' command"""
    template = utils.read_text(pkg_resources.resource_filename("pychado", "sql/stats.sql"))
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
    """Replaces a placeholder in a query with a condition restricting results to a certain organism"""
    if arguments.organism == "all":
        modified_query = query.replace(':ORGANISM_CONDITION', 'TRUE')
    else:
        modified_query = query.replace(':ORGANISM_CONDITION', "abbreviation = :organism")
    return modified_query


def set_database_condition(query: str, arguments) -> str:
    """Replaces a placeholder in a query with a condition restricting results to a certain database"""
    if arguments.database == "all":
        modified_query = query.replace(':DB_CONDITION', 'TRUE')
    else:
        modified_query = query.replace(':DB_CONDITION', "db.name = :database_name")
    return modified_query


def set_vocabulary_condition(query: str, arguments) -> str:
    """Replaces a placeholder in a query with a condition restricting results to a certain vocabulary"""
    if arguments.vocabulary == "all":
        modified_query = query.replace(':CV_CONDITION', 'TRUE')
    else:
        modified_query = query.replace(':CV_CONDITION', "cv.name = :cv_name")
    return modified_query


def specify_list_parameters(specifier: str, arguments) -> dict:
    """Specifies the parameters that complete the SQL query of a 'chado list' command"""
    params = {}
    if specifier == "cvterms":
        if arguments.vocabulary != "all":
            params["cv_name"] = arguments.vocabulary
        if arguments.database != "all":
            params["database_name"] = arguments.database
    elif specifier == "genedb_products":
        if arguments.organism != "all":
            params["organism"] = arguments.organism
    elif specifier == "organisms":
        pass
    else:
        print("Functionality 'list " + specifier + "' is not yet implemented.")
    return params


def specify_stats_parameters(arguments) -> dict:
    """Specifies the parameters that complete the SQL query of a 'chado stats' command"""
    end_date = arguments.end_date
    if not end_date:
        end_date = utils.current_date()
    params = {"start_date": arguments.start_date, "end_date": end_date}
    if arguments.organism != "all":
        params["organism"] = arguments.organism
    return params


def specify_insert_parameters(specifier: str, arguments) -> dict:
    """Specifies the parameters that complete the SQL query of a 'chado insert' command"""
    params = {}
    if specifier == "organism":
        if not arguments.common_name:
            arguments.common_name = arguments.abbreviation
        params["genus"] = arguments.genus
        params["species"] = arguments.species
        params["abbreviation"] = arguments.abbreviation
        params["common_name"] = arguments.common_name
        params["comment"] = arguments.comment
    else:
        print("Functionality 'insert " + specifier + "' is not yet implemented.")
    return params


def specify_delete_parameters(specifier: str, arguments) -> dict:
    """Specifies the parameters that complete the SQL query of a 'chado delete' command"""
    params = {}
    if specifier == "organism":
        params["organism"] = arguments.organism
    else:
        print("Functionality 'delete " + specifier + "' is not yet implemented.")
    return params
