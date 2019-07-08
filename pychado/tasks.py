from . import utils, dbutils, queries, ddl
from .io import direct, essentials, ontology, fasta, gff, gaf


def check_access(connection_uri: str, task: str) -> bool:
    """Checks if the database of interest exists and is accessible. If the database doesn't exist, but the
    task implies its creation, create it. Otherwise exit the program."""
    exists = dbutils.exists(connection_uri)
    if exists:
        if task in ["create", "restore"]:
            # Database already exists, we should not overwrite it. Return without further action
            print("Database already exists. Overwriting is not permitted.")
            return False
        else:
            # Database exists, that's all we need
            return True
    else:
        if task in ["create", "restore"]:
            # Database doesn't exist, but task implies its creation
            return True
        else:
            # Database doesn't exist, and task can't be completed. Return without further action
            print("Database does not exist. Task can't be completed.")
            return False


def run_command_with_arguments(command: str, sub_command: str, arguments, connection_uri: str) -> None:
    """Runs a specified sub-command with the supplied arguments"""

    # Run the command
    if command == "connect":
        # Connect to a PostgreSQL database for an interactive session
        dbutils.connect_to_database(connection_uri)
    elif command == "admin" and sub_command == "create":
        # Create a PostgreSQL database
        dbutils.create_database(connection_uri)
    elif command == "admin" and sub_command == "drop":
        # Drop a PostgreSQL database
        dbutils.drop_database(connection_uri)
    elif command == "admin" and sub_command == "dump":
        # Dump a PostgreSQL database into an archive file
        dbutils.dump_database(connection_uri, arguments.archive)
    elif command == "admin" and sub_command == "restore":
        # Restore a PostgreSQL database from an archive file
        dbutils.create_database(connection_uri)
        dbutils.restore_database(connection_uri, arguments.archive)
    elif command == "admin" and sub_command == "setup":
        # Setup a PostgreSQL database according to a schema
        run_setup_command(arguments, connection_uri)
    elif command == "admin" and sub_command == "grant":
        # Grant access to objects in a PostgreSQL database
        run_grant_revoke_command(arguments, connection_uri, True)
    elif command == "admin" and sub_command == "revoke":
        # Revoke access to objects in a PostgreSQL database
        run_grant_revoke_command(arguments, connection_uri, False)
    elif command == "query":
        # Query a PostgreSQL database and export the result to a text file
        run_query_command(arguments, connection_uri)
    elif command == "execute":
        # Run a function defined in a PostgreSQL database
        run_execute_command(sub_command, arguments, connection_uri)
    elif command == "extract":
        # Run a pre-compiled query against the CHADO database
        run_select_command(sub_command, arguments, connection_uri)
    elif command == "insert":
        # Insert a new entity of a specified type into the CHADO database
        run_insert_command(sub_command, arguments, connection_uri)
    elif command == "delete":
        # Delete an entity of a specified type from the CHADO database
        run_delete_command(sub_command, arguments, connection_uri)
    elif command == "import":
        # Import data from file into the CHADO database
        run_import_command(sub_command, arguments, connection_uri)
    elif command == "export":
        # Export data from the CHADO database to file
        run_export_command(sub_command, arguments, connection_uri)
    else:
        print("Functionality '" + command + "' is not yet implemented.")


def run_setup_command(arguments, uri: str) -> None:
    """Sets up a PostgreSQL database according to a schema"""
    if arguments.schema_file or arguments.schema == "gmod":
        schema_file = arguments.schema_file
        if not schema_file:
            schema_file = utils.download_file(dbutils.default_schema_url())
        dbutils.setup_database(uri, schema_file)
    else:
        if arguments.schema == "basic":
            client = ddl.PublicSchemaSetupClient(uri)
        elif arguments.schema == "audit":
            client = ddl.AuditSchemaSetupClient(uri)
        elif arguments.schema == "audit_backup":
            client = ddl.AuditBackupSchemaSetupClient(uri)
        else:
            client = ddl.DDLClient(uri)
        client.create()


def run_grant_revoke_command(arguments, uri: str, grant_access: bool) -> None:
    """Grant/revoke access to objects in a PostgreSQL database"""
    client = ddl.RolesClient(uri)
    if grant_access:
        client.grant_or_revoke(arguments.role, arguments.schema, arguments.write, True)
    else:
        client.grant_or_revoke(arguments.role, arguments.schema, False, False)


def run_query_command(arguments, uri: str) -> None:
    """Query a PostgreSQL database and export the result to a text file"""
    query = (arguments.query or utils.read_text(arguments.input_file))
    dbutils.query_and_print(uri, query, arguments.output_file, arguments.format, arguments.include_header,
                            arguments.delimiter)
    if arguments.output_file:
        print("Data exported to " + arguments.output_file)


def run_execute_command(specifier: str, arguments, uri: str) -> None:
    """Run a function defined in the database"""
    if specifier == "audit_backup":
        client = ddl.AuditBackupSchemaSetupClient(uri)
        client.execute_backup_function(arguments.date)
    else:
        print("Functionality 'execute " + specifier + "' is not yet implemented.")


def run_select_command(specifier: str, arguments, uri: str) -> None:
    """Run a pre-compiled query against a database"""
    # Load query template
    if hasattr(arguments, "public_only") and arguments.public_only:
        modified_specifier = "public_" + specifier
        template = queries.load_query(modified_specifier)
    else:
        template = queries.load_query(specifier)

    # Bind query parameters
    if specifier == "organisms":
        query = template
    elif specifier == "cvterms":
        query = queries.set_query_conditions(template, database=arguments.database, vocabulary=arguments.vocabulary)
    elif specifier == "gene_products":
        query = queries.set_query_conditions(template, organism=arguments.organism)
    elif specifier == "annotation_updates":
        query = queries.set_query_conditions(template, organism=arguments.organism, start_date=arguments.start_date,
                                             end_date=(arguments.end_date or utils.current_date()))
    elif specifier == "curator_comments":
        query = queries.set_query_conditions(template, organism=arguments.organism)
    else:
        print("Functionality 'extract " + specifier + "' is not yet implemented.")
        return

    # Execute query
    dbutils.query_and_print(uri, query, arguments.output_file, arguments.format, arguments.include_header,
                            arguments.delimiter)
    if arguments.output_file:
        print("Data exported to " + arguments.output_file)


def run_insert_command(specifier: str, arguments, uri: str) -> None:
    """Insert a new entity of a specified type into a database"""
    client = direct.DirectIOClient(uri, arguments.verbose)
    if specifier == "organism":
        client.insert_organism(arguments.genus, arguments.species, arguments.abbreviation, arguments.common_name,
                               arguments.infraspecific_name, arguments.comment, arguments.genome_version,
                               arguments.taxon_id, arguments.wikidata_id)
    else:
        print("Functionality 'insert " + specifier + "' is not yet implemented.")


def run_delete_command(specifier: str, arguments, uri: str) -> None:
    """Delete an entity of a specified type from a database"""
    client = direct.DirectIOClient(uri, arguments.verbose)
    if specifier == "organism":
        client.delete_organism(arguments.organism)
    else:
        print("Functionality 'delete " + specifier + "' is not yet implemented.")


def run_import_command(specifier: str, arguments, uri: str) -> None:
    """Imports data from a file into a database"""
    file = None
    if hasattr(arguments, "input_file") and arguments.input_file:
        file = arguments.input_file
    elif hasattr(arguments, "input_url") and arguments.input_url:
        file = utils.download_file(arguments.input_url)

    if specifier == "essentials":
        client = essentials.EssentialsClient(uri, arguments.verbose)
        client.load()
    elif specifier == "ontology":
        client = ontology.OntologyClient(uri, arguments.verbose)
        client.load(file, arguments.format, arguments.database_authority)
    elif specifier == "gff":
        client = gff.GFFImportClient(uri, arguments.verbose)
        client.load(file, arguments.organism, arguments.fasta, arguments.sequence_type, arguments.fresh_load,
                    arguments.force, arguments.full_genome, arguments.full_attributes)
    elif specifier == "fasta":
        client = fasta.FastaImportClient(uri, arguments.verbose)
        client.load(file, arguments.organism, arguments.sequence_type)
    elif specifier == "gaf":
        client = gaf.GAFImportClient(uri, arguments.verbose)
        client.load(file, arguments.organism, arguments.annotation_level)
    else:
        print("Functionality 'import " + specifier + "' is not yet implemented.")


def run_export_command(specifier: str, arguments, uri: str) -> None:
    """Exports data from a database to a file"""
    if specifier == "fasta":
        client = fasta.FastaExportClient(uri, arguments.verbose)
        client.export(arguments.output_file, arguments.organism, arguments.sequence_type, arguments.release,
                      arguments.include_obsolete)
    elif specifier == "gff":
        client = gff.GFFExportClient(uri, arguments.verbose)
        client.export(arguments.output_file, arguments.organism, arguments.export_fasta, arguments.fasta_file,
                      arguments.include_obsolete)
    elif specifier == "gaf":
        client = gaf.GAFExportClient(uri, arguments.verbose)
        client.export(arguments.output_file, arguments.organism, arguments.database_authority,
                      arguments.annotation_level, arguments.include_obsolete)
    else:
        print("Functionality 'export " + specifier + "' is not yet implemented.")
