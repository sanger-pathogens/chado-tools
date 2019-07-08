import sys
import os
import pkg_resources
import argparse
import time
from . import tasks, dbutils


def main():
    """Main routine of the chado-tools package"""

    # Parse the supplied command line arguments
    arguments = parse_arguments(sys.argv)
    command = sys.argv[1]
    sub_command = ""
    if command in wrapper_commands():
        sub_command = sys.argv[2]

    # Check database access
    start_time = time.time()
    connection_params = dbutils.get_connection_parameters(arguments.config, arguments.use_password, arguments.dbname)
    connection_string = dbutils.generate_uri(connection_params)
    if tasks.check_access(connection_string, sub_command):

        # Run the command
        tasks.run_command_with_arguments(command, sub_command, arguments, connection_string)

    # Print run time
    if arguments.verbose:
        print("Runtime: {0:.2f} s".format(time.time()-start_time))


def general_commands() -> dict:
    """Lists the available general sub-commands of the 'chado' command with corresponding descriptions"""
    return {
        "connect": "connect to a CHADO database for an interactive session",
        "query": "query a CHADO database and export the result to a text file"
    }


def wrapper_commands() -> dict:
    """Lists the available 'wrapper' sub-commands of the 'chado' command with corresponding descriptions"""
    return {
        "extract": "run a pre-compiled query against the CHADO database",
        "insert": "insert a new entity of a specified type into the CHADO database",
        "delete": "delete an entity of a specified type from the CHADO database",
        "import": "import data from file into the CHADO database",
        "export": "export data from the CHADO database to file",
        "execute": "execute a function defined in a CHADO database",
        "admin": "perform administrative tasks, such as creating or dumping a CHADO database"
    }


def admin_commands() -> dict:
    """Lists the available sub-commands of the 'chado admin' command with corresponding descriptions"""
    return {
        "create": "create a new CHADO database",
        "drop": "drop a CHADO database",
        "dump": "dump a CHADO database into an archive file",
        "restore": "restore a CHADO database from an archive file",
        "setup": "set up a blank CHADO database according to a given schema",
        "grant": "grant privileges for a CHADO database to a user/role",
        "revoke": "revoke privileges for a CHADO database from a user/role"
    }


def extract_commands() -> dict:
    """Lists the available sub-commands of the 'chado extract' command with corresponding descriptions"""
    return {
        "organisms": "list all organisms in the CHADO database",
        "cvterms": "list all CV terms in the CHADO database",
        "gene_products": "list all products of transcripts in the CHADO database",
        "annotation_updates": "list annotation updates in a CHADO database",
        "curator_comments": "list curator comments to genes and gene products in a CHADO database"
    }


def insert_commands() -> dict:
    """Lists the available sub-commands of the 'chado insert' command with corresponding descriptions"""
    return {
        "organism": "insert an organism into the CHADO database"
    }


def delete_commands() -> dict:
    """Lists the available sub-commands of the 'chado delete' command with corresponding descriptions"""
    return {
        "organism": "delete an organism from the CHADO database"
    }


def import_commands() -> dict:
    """Lists the available sub-commands of the 'chado import' command with corresponding descriptions"""
    return {
        "essentials": "import basic terms into the CHADO database (for setup)",
        "ontology": "import an ontology into the CHADO database",
        "fasta": "import sequences from a FASTA file into the CHADO database",
        "gff": "import genomic data from a GFF3 file into the CHADO database",
        "gaf": "import gene annotation data from a GAF file into the CHADO database"
    }


def export_commands() -> dict:
    """Lists the available sub-commands of the 'chado export' command with corresponding descriptions"""
    return {
        "fasta": "export genome/protein sequences from the CHADO database to a FASTA file",
        "gff": "export genomic data from the CHADO database to a GFF3 file",
        "gaf": "export gene annotation data from the CHADO database to a GAF file"
    }


def execute_commands() -> dict:
    """Lists the available sub-commands of the 'chado execute' command with corresponding descriptions"""
    return {
        "audit_backup": "backs up the audit tables to a separate schema"
    }


def parse_arguments(input_arguments: list) -> argparse.Namespace:
    """Defines the formal arguments of the 'chado' command and parses the actual arguments accordingly"""

    # Create a parser and add global formal arguments
    program_name = os.path.basename(input_arguments[0])
    parser = argparse.ArgumentParser(description="Tools to access CHADO databases",
                                     epilog="For detailed usage information type '" + program_name + " <command> -h'",
                                     prog=program_name, allow_abbrev=False)
    parser.add_argument("-v", "--version", help="show the version of the software and exit",
                        action='version', version=str(pkg_resources.get_distribution("chado-tools").version))

    # Add subparsers for all sub-commands
    subparsers = parser.add_subparsers()

    for command, description in general_commands().items():
        # Create subparser and add general and specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_general_arguments(sub)
        add_arguments_by_command(command, sub)

    for command, description in wrapper_commands().items():
        # Create subparser and add specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_arguments_by_command(command, sub)

    # Parse the actual arguments
    return parser.parse_args(input_arguments[1:])


def add_general_arguments(parser: argparse.ArgumentParser):
    """Defines general formal arguments (available to all sub-commands)"""
    parser.add_argument("-V", "--verbose", action="store_true", help="verbose mode")
    parser_group = parser.add_mutually_exclusive_group(required=False)
    parser_group.add_argument("-c", "--config", default="", help="YAML file containing connection details")
    parser_group.add_argument("-p", "--use_password", action="store_true",
                              help="connect with password (default: no password)")
    parser.add_argument("dbname", help="name of the database")


def add_general_extract_arguments(parser: argparse.ArgumentParser):
    """Defines general formal arguments for all sub-commands that export data from a database"""
    parser.add_argument("-H", "--include_header", action="store_true",
                        help="include header in CSV output (default: False)")
    parser.add_argument("-d", "--delimiter", default="\t",
                        help="Character delimiting fields in CSV output (default: tab)")
    parser.add_argument("-o", "--output_file", default="", help="file into which data are exported (default: stdout)")
    parser.add_argument("-F", "--format", default="csv", choices=["csv", "json"],
                        help="format of the file (default: csv)")


def add_arguments_by_command(command: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command"""
    if command == "connect":
        pass
    elif command == "admin":
        add_admin_arguments(parser)
    elif command == "query":
        add_query_arguments(parser)
    elif command == "execute":
        add_execute_arguments(parser)
    elif command == "extract":
        add_extract_arguments(parser)
    elif command == "insert":
        add_insert_arguments(parser)
    elif command == "delete":
        add_delete_arguments(parser)
    elif command == "import":
        add_import_arguments(parser)
    elif command == "export":
        add_export_arguments(parser)
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_admin_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado admin' sub-command"""
    parser.epilog = "For detailed usage information type '" + parser.prog + " <command> -h'"
    subparsers = parser.add_subparsers()
    for command, description in admin_commands().items():
        # Create subparser and add general and specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_general_arguments(sub)
        add_admin_arguments_by_command(command, sub)


def add_admin_arguments_by_command(command: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command of 'chado admin'"""
    if command == "create":
        pass
    elif command == "drop":
        pass
    elif command == "dump":
        add_dump_arguments(parser)
    elif command == "restore":
        add_restore_arguments(parser)
    elif command == "setup":
        add_setup_arguments(parser)
    elif command == "grant":
        add_grant_arguments(parser)
    elif command == "revoke":
        add_revoke_arguments(parser)
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_dump_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado admin dump' sub-command"""
    parser.add_argument("archive", help="archive file to be created")


def add_restore_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado admin restore' sub-command"""
    parser.add_argument("archive", help="archive file")


def add_setup_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado admin setup' sub-command"""
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-s", "--schema", choices=["gmod", "basic", "audit", "audit_backup"], default="gmod",
                       help="Database schema (default: GMOD schema 1.31)")
    group.add_argument("-f", "--schema_file", default="", help="File with database schema")


def add_grant_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado admin grant' sub-command"""
    parser.add_argument("-r", "--role", required=True, help="Name of the role/user")
    parser.add_argument("-s", "--schema", help="Database schema (default: all)")
    parser.add_argument("-w", "--write", action="store_true", help="Grant read-write access (default: read-only)")


def add_revoke_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado admin revoke' sub-command"""
    parser.add_argument("-r", "--role", required=True, help="Name of the role/user")
    parser.add_argument("-s", "--schema", help="Database schema (default: all)")


def add_query_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado query' sub-command"""
    add_general_extract_arguments(parser)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--input_file", default="", help="file containing an SQL query")
    group.add_argument("-q", "--query", default="", help="SQL query")


def add_execute_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado execute' sub-command"""
    parser.epilog = "For detailed usage information type '" + parser.prog + " <command> -h'"
    subparsers = parser.add_subparsers()
    for command, description in execute_commands().items():
        # Create subparser and add general and specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_general_arguments(sub)
        add_execute_arguments_by_command(command, sub)


def add_execute_arguments_by_command(command: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command of 'chado execute'"""
    if command == "audit_backup":
        add_execute_backup_arguments(parser)
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_execute_backup_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado execute audit_backup' sub-command"""
    parser.add_argument("--date", required=True, help="date for maximum age of logs to remain in main audit tables, "
                                                      "format 'YYYYMMDD'")


def add_extract_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado extract' sub-command"""
    parser.epilog = "For detailed usage information type '" + parser.prog + " <command> -h'"
    subparsers = parser.add_subparsers()
    for command, description in extract_commands().items():
        # Create subparser and add general and specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_general_arguments(sub)
        add_general_extract_arguments(sub)
        add_extract_arguments_by_command(command, sub)


def add_extract_arguments_by_command(command: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command of 'chado extract'"""
    if command == "organisms":
        add_extract_organisms_arguments(parser)
    elif command == "cvterms":
        add_extract_cvterms_arguments(parser)
    elif command == "gene_products":
        add_extract_gene_product_arguments(parser)
    elif command == "annotation_updates":
        add_extract_annotation_updates_arguments(parser)
    elif command == "curator_comments":
        add_extract_curator_comments_arguments(parser)
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_extract_organisms_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado extract organisms' sub-command"""
    parser.add_argument("--public_only", action="store_true", help="only extract public genomes (default: extract all)")


def add_extract_cvterms_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado extract cvterms' sub-command"""
    parser.add_argument("--vocabulary", help="restrict to a vocabulary, e.g. 'relationship'")
    parser.add_argument("--database", help="restrict to a database, e.g. 'GO'")


def add_extract_gene_product_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado extract gene_products' sub-command"""
    parser.add_argument("-a", "--abbreviation", dest="organism",
                        help="restrict to a certain organism, defined by its abbreviation/short name (default: all)")
    parser.add_argument("--public_only", action="store_true", help="restrict to public genomes (default: all)")


def add_extract_annotation_updates_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado extract annotation_updates' sub-command"""
    parser.add_argument("-a", "--abbreviation", dest="organism",
                        help="restrict to a certain organism, defined by its abbreviation/short name (default: all)")
    parser.add_argument("--start_date", required=True, help="date for maximum age of updates, format 'YYYYMMDD'")
    parser.add_argument("--end_date", default="", help="date for minimum age of updates, format 'YYYYMMDD' "
                                                       "(default: today)")
    parser.add_argument("--public_only", action="store_true", help="restrict to public genomes (default: all)")


def add_extract_curator_comments_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado extract curator_comments' sub-command"""
    parser.add_argument("-a", "--abbreviation", dest="organism",
                        help="restrict to a certain organism, defined by its abbreviation/short name (default: all)")
    parser.add_argument("--public_only", action="store_true", help="restrict to public genomes (default: all)")


def add_insert_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado insert' sub-command"""
    parser.epilog = "For detailed usage information type '" + parser.prog + " <command> -h'"
    subparsers = parser.add_subparsers()
    for command, description in insert_commands().items():
        # Create subparser and add general and specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_general_arguments(sub)
        add_insert_arguments_by_command(command, sub)


def add_insert_arguments_by_command(command: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command of 'chado insert'"""
    if command == "organism":
        add_insert_organism_arguments(parser)
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_insert_organism_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado insert organism' sub-command"""
    parser.add_argument("-g", "--genus", required=True, help="genus of the organism")
    parser.add_argument("-s", "--species", required=True, help="species of the organism")
    parser.add_argument("-i", "--infraspecific_name", default="", help="infraspecific name (strain) of the organism")
    parser.add_argument("-a", "--abbreviation", required=True, help="abbreviation/short name of the organism")
    parser.add_argument("--common_name", default="",
                        help="common name of the organism (default: use abbreviation, if provided)")
    parser.add_argument("--comment", help="comment")
    parser.add_argument("--genome_version", help="version number of the genome")
    parser.add_argument("--taxon_id", help="NCBI taxon ID")
    parser.add_argument("--wikidata_id", help="ID of the organism on Wikidata")


def add_delete_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado delete' sub-command"""
    parser.epilog = "For detailed usage information type '" + parser.prog + " <command> -h'"
    subparsers = parser.add_subparsers()
    for command, description in delete_commands().items():
        # Create subparser and add general and specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_general_arguments(sub)
        add_delete_arguments_by_command(command, sub)


def add_delete_arguments_by_command(command: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command of 'chado delete'"""
    if command == "organism":
        add_delete_organism_arguments(parser)
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_delete_organism_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado delete organism' sub-command"""
    parser.add_argument("-a", "--abbreviation", required=True, dest="organism",
                        help="abbreviation/short name of the organism")


def add_import_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado import' sub-command"""
    parser.epilog = "For detailed usage information type '" + parser.prog + " <command> -h'"
    subparsers = parser.add_subparsers()
    for command, description in import_commands().items():
        # Create subparser and add general and specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_general_arguments(sub)
        add_import_arguments_by_command(command, sub)


def add_import_arguments_by_command(command: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command of 'chado import'"""
    if command == "essentials":
        pass
    elif command == "ontology":
        add_import_ontology_arguments(parser)
    elif command == "gff":
        add_import_gff_arguments(parser)
    elif command == "fasta":
        add_import_fasta_arguments(parser)
    elif command == "gaf":
        add_import_gaf_arguments(parser)
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_import_ontology_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado import ontology' sub-command"""
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--input_file", default="", help="file containing CV terms")
    group.add_argument("-u", "--input_url", default="", help="URL to a file containing CV terms")
    parser.add_argument("-A", "--database_authority", required=True,
                        help="database authority of the terms in the file, e.g. 'GO'")
    parser.add_argument("-F", "--format", default="obo", choices=["obo", "owl"],
                        help="format of the file (default: obo)")


def add_import_gff_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado import gff' sub-command"""
    parser.add_argument("-f", "--input_file", required=True, help="GFF3 input file")
    parser.add_argument("-a", "--abbreviation", required=True, dest="organism",
                        help="abbreviation/short name of the organism")
    parser.add_argument("--fasta", help="FASTA input file with sequences")
    parser.add_argument("-t", "--sequence_type", choices=["chromosome", "supercontig", "contig", "region"],
                        default="region", help="type of the FASTA sequences, if present (default: region)")
    parser.add_argument("--fresh_load", action="store_true",
                        help="load a genome from scratch (default: load an update to an existing genome)")
    parser.add_argument("--force", action="store_true",
                        help="in case of a fresh load, purge all existing features of the organism")
    parser.add_argument("--full_genome", action="store_true",
                        help="in case of an update, mark features not present in the input file as obsolete")
    parser.add_argument("--full_attributes", action="store_true",
                        help="in case of an update, delete feature attributes not present in the input file")


def add_import_fasta_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado import fasta' sub-command"""
    parser.add_argument("-f", "--input_file", required=True, help="FASTA input file")
    parser.add_argument("-a", "--abbreviation", required=True, dest="organism",
                        help="abbreviation/short name of the organism")
    parser.add_argument("-t", "--sequence_type", choices=["chromosome", "supercontig", "contig", "region"],
                        default="region", help="type of the sequences (default: region)")


def add_import_gaf_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado import gaf' sub-command"""
    parser.add_argument("-f", "--input_file", required=True, help="GFF3 input file")
    parser.add_argument("-a", "--abbreviation", required=True, dest="organism",
                        help="abbreviation/short name of the organism")
    parser.add_argument("-L", "--annotation_level", choices=["default", "gene", "transcript", "protein"],
                        default="default", help="level to which GO terms are related in the database (default: "
                                                "same level as in the input file)")


def add_export_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado export' sub-command"""
    parser.epilog = "For detailed usage information type '" + parser.prog + " <command> -h'"
    subparsers = parser.add_subparsers()
    for command, description in export_commands().items():
        # Create subparser and add general and specific formal arguments
        sub = subparsers.add_parser(command, description=description, help=description)
        add_general_arguments(sub)
        add_export_arguments_by_command(command, sub)


def add_export_arguments_by_command(command: str, parser: argparse.ArgumentParser):
    """Defines formal arguments for a specified sub-command of 'chado export'"""
    if command == "fasta":
        add_export_fasta_arguments(parser)
    elif command == "gff":
        add_export_gff_arguments(parser)
    elif command == "gaf":
        add_export_gaf_arguments(parser)
    else:
        print("Command '" + parser.prog + "' is not available.")


def add_export_fasta_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado export fasta' sub-command"""
    parser.add_argument("-f", "--output_file", required=True, help="FASTA output file")
    parser.add_argument("-a", "--abbreviation", required=True, dest="organism",
                        help="abbreviation/short name of the organism")
    parser.add_argument("-t", "--sequence_type", required=True, choices=["contigs", "genes", "proteins"],
                        help="type of the sequences to be exported")
    parser.add_argument("-r", "--release", help="name of the FASTA release")
    parser.add_argument("--include_obsolete", action="store_true", help="export all features, including obsoletes")


def add_export_gff_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado export gff' sub-command"""
    parser.add_argument("-f", "--output_file", required=True, help="GFF output file")
    parser.add_argument("-a", "--abbreviation", required=True, dest="organism",
                        help="abbreviation/short name of the organism")
    parser.add_argument("--export_fasta", action="store_true", help="export FASTA sequences along with annotations")
    parser.add_argument("--fasta_file", help="FASTA output file with sequences (default: paste to end of GFF file)")
    parser.add_argument("--include_obsolete", action="store_true", help="export all features, including obsoletes")


def add_export_gaf_arguments(parser: argparse.ArgumentParser):
    """Defines formal arguments for the 'chado export gff' sub-command"""
    parser.add_argument("-f", "--output_file", required=True, help="GAF output file")
    parser.add_argument("-a", "--abbreviation", required=True, dest="organism",
                        help="abbreviation/short name of the organism")
    parser.add_argument("-A", "--database_authority", required=True,
                        help="database from which the file is created, e.g. 'UniProtKB'")
    parser.add_argument("-L", "--annotation_level", choices=["default", "gene", "transcript", "protein"],
                        default="default", help="level to which GO terms are related in the output file (default: "
                                                "same level as in the database)")
    parser.add_argument("--include_obsolete", action="store_true", help="export all features, including obsoletes")
