import pkg_resources
from pychado import utils


def load_list_query(specifier: str, arguments) -> str:
    """Loads the SQL query for a 'chado list' command"""
    query = ""
    if specifier == "organisms":
        template = utils.read_text(pkg_resources.resource_filename("pychado", "sql/list_organisms.sql"))
        query = set_organism_condition(template, arguments)
    elif specifier == "genera":
        query = utils.read_text(pkg_resources.resource_filename("pychado", "sql/list_genera.sql"))
    elif specifier == "products":
        template = utils.read_text(pkg_resources.resource_filename("pychado", "sql/list_products.sql"))
        query = set_organism_condition(template, arguments)
    return query


def load_stats_query(arguments) -> str:
    """Loads the SQL query for a 'chado stats' command"""
    template = utils.read_text(pkg_resources.resource_filename("pychado", "sql/stats.sql"))
    query = set_organism_condition(template, arguments)
    return query


def set_organism_condition(query: str, arguments) -> str:
    """Replaces a placeholder in a query with a condition restricting results to certain organisms"""
    if not hasattr(arguments, "genus") or arguments.genus == "all":
        modified_query = query.replace('{{CONDITION}}', 'TRUE')
    elif arguments.genus != "all" and (not hasattr(arguments, "species") or arguments.species == "all"):
        condition = utils.read_text(pkg_resources.resource_filename("pychado", "sql/condition_genus.sql"))
        modified_query = query.replace('{{CONDITION}}', condition)
    else:
        condition = utils.read_text(pkg_resources.resource_filename("pychado",
                                                                    "sql/condition_genus_species.sql"))
        modified_query = query.replace('{{CONDITION}}', condition)
    return modified_query


def specify_list_parameters(specifier: str, arguments) -> tuple:
    """Specifies the parameters that complete the SQL query of a 'chado list' command"""
    if specifier == "organisms":
        if arguments.genus != "all":
            params = (arguments.genus,)
        else:
            params = tuple()
    elif specifier == "products":
        if arguments.genus != "all" and arguments.species != "all":
            params = (arguments.genus, arguments.species)
        elif arguments.genus != "all" and arguments.species == "all":
            params = (arguments.genus,)
        else:
            params = tuple()
    else:
        params = tuple()
    return params


def specify_stats_parameters(arguments) -> tuple:
    """Specifies the parameters that complete the SQL query of a 'chado stats' command"""
    if arguments.genus != "all" and arguments.species != "all":
        params = (arguments.date, arguments.genus, arguments.species)
    elif arguments.genus != "all" and arguments.species == "all":
        params = (arguments.date, arguments.genus)
    else:
        params = (arguments.date,)
    return params
