from pychado import utils
import subprocess
# import psycopg2


def connect(configurationFile):
    """Connects to a SQL database and brings back a command line prompt"""

    # Read connection parameters from a configuration file
    connectionDetails = dict(utils.parseYaml(configurationFile))

    # Create a URI
    connectionURI = ["postgresql://"]
    if 'user' in connectionDetails:
        connectionURI.append(connectionDetails['user'])
        if 'password' in connectionDetails:
            connectionURI.append(":" + connectionDetails['password'])
        connectionURI.append("@")
    if 'host' in connectionDetails:
        connectionURI.append(connectionDetails['host'])
    if 'port' in connectionDetails:
        connectionURI.append(":" + str(connectionDetails['port']))
    if 'database' in connectionDetails:
        connectionURI.append("/" + connectionDetails['database'])

    # Establish a connection to an SQL server
    try:
        print("Establishing connection to database...")
        command = ["psql", ''.join(connectionURI)]
        subprocess.run(command)
        print("Connection to database closed.")
    except:
        print("Unable to connect to database.")
