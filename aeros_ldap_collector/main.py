__name__ = "aerOS LDAP Collector"
__version__ = "1.1.2"
__author__ = "David Martínez García"
__credits__ = ["GIROS DIT-UPM", "Luis Bellido Triana", "Daniel González Sánchez", "David Martínez García"]

## -- BEGIN IMPORT STATEMENTS -- ##

import configparser
from contextlib import asynccontextmanager
from fastapi import FastAPI
import json
from kafka import KafkaProducer
from ldap3 import Server, Connection, ALL, ALL_ATTRIBUTES
import logging
import time

## -- END IMPORT STATEMENTS -- ##

## -- BEGIN CONSTANTS DECLARATION -- ##

# The configuration file is always expected to be located at this path:
CONFIG_FILE_PATH = "/aeros-ldap-collector/files/config.ini"

### CONFIGURATION SECTIONS AND DIRECTIVES ###

REQUIRED_CONFIG_SECTIONS = [
    "ldap.general", "ldap.connection", "output"
]

LDAP_GENERAL_REQUIRED_CONF_DIRECTIVES = [
    "organization_dn"
]

LDAP_CONNECTION_REQUIRED_CONF_DIRECTIVES = [
    "server_endpoint", "use_ssl", "user", "password", "max_retries", "timeout"
]

OUTPUT_KAFKA_REQUIRED_DIRECTIVES = [
    "kafka_server", "kafka_topic"
]

### --- ###

## -- END CONSTANTS DECLARATION -- ##

## -- BEGIN LOGGING CONFIGURATION -- ## 

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

## -- END LOGGING CONFIGURATION -- ##

## -- BEGIN LOADING CONFIGURATION DIRECTIVES -- ##

config = configparser.ConfigParser()
config.read(CONFIG_FILE_PATH)

## -- END LOADING CONFIGURATION DIRECTIVES -- ##

## -- BEGIN DEFINITION OF AUXILIARY FUNCTIONS AND VARIABLES -- ##

def check_config(config: configparser.ConfigParser):
    """
    Checks if the configuration directives are valid, this is, the configuration file
    is correct in its entirety.
    """
    logger.info("Checking configuration file...")

    config_sections = config.sections()

    if not config_sections:
        logger.error("Configuration file is invalid")
        raise RuntimeError("Configuration file is invalid")
    else:
        if config_sections != REQUIRED_CONFIG_SECTIONS:
            logger.error("Missing or invalid configuration sections")
            logger.error("Provided configuration sections: " + str(config_sections))
            logger.error("Required configuration sections: " + str(REQUIRED_CONFIG_SECTIONS))
            raise RuntimeError("Missing or invalid configuration sections")
        else:
            for config_section in config_sections:
                if config_section != "output" and not config[config_section]:
                    logger.error("No directives found in required configuration section: " + config_section)
                    raise RuntimeError("No directives found in required configuration section: " + config_section)
                else:
                    directives = []
                    for directive in config[config_section]:
                        directives.append(directive)
                    if config_section == "ldap.general":
                        if directives != LDAP_GENERAL_REQUIRED_CONF_DIRECTIVES:
                            logger.error("Missing or invalid required configuration directives for ldap.general section")
                            logger.error("Provided configuration directives: " + str(directives))
                            logger.error("Required configuration directives: " + str(LDAP_GENERAL_REQUIRED_CONF_DIRECTIVES))
                            raise RuntimeError("Missing or invalid configuration directives for ldap.general section")
                    if config_section == "ldap.connection":
                        if directives != LDAP_CONNECTION_REQUIRED_CONF_DIRECTIVES:
                            logger.error("Missing or invalid required configuration directives for ldap.connection section")
                            logger.error("Provided configuration directives: " + str(directives))
                            logger.error("Required configuration directives: " + str(LDAP_CONNECTION_REQUIRED_CONF_DIRECTIVES))
                            raise RuntimeError("Missing or invalid configuration directives for ldap.connection section")
                    if config_section == "output":
                        kafka_directives = []
                        for directive in directives:
                            if "kafka_" in directive:
                                kafka_directives.append(directive)
                        if (len(kafka_directives) != 0) and (kafka_directives != OUTPUT_KAFKA_REQUIRED_DIRECTIVES):
                            logger.error("Missing or invalid configuration directives for Kafka in output section")
                            logger.error("Provided directives: " + str(kafka_directives))
                            logger.error("Required directives: " + str(OUTPUT_KAFKA_REQUIRED_DIRECTIVES))
                            raise RuntimeError("Missing or invalid configuration directives for Kafka in output section")

    logger.info("Configuration file checked")

def establish_connection(server: Server, user: str, password: str, max_retries: int, timeout: int) -> Connection:
    """
    Tries to establish a connection to the LDAP server.
    This function will try to establish the connection within a maximum number of retries of specified timeout.
    """
    logger.info("Trying to establish a connection to the following LDAP server: " + str(server))

    for retry in range(1, max_retries + 1):
        try:
            logger.info("Retry: " + str(retry))
            connection = Connection(server, user, password, auto_bind=True)
        except Exception as e:
            logger.exception("The connection to the LDAP server could not be established: %s" % e)
            if retry == max_retries:
                raise RuntimeError("The connection to the LDAP server could not be established: %s" % e)
            else:
                logger.info("Waiting " + str(timeout) + " seconds before trying again")
                time.sleep(timeout)
                continue
        if connection is not None:
            logger.info("Connection sucessfully established")
            break
    
    return connection

def retrieve_information(connection: Connection, organization_dn: str):
    """
    Retrieves LDAP information for users, roles, groups and organizations, and returns it JSON objects.
    """
    logger.info("Trying to retrieve LDAP information...")

    # Retrieve users:
    try:
        logger.info("Trying to retrieve LDAP information for users...")
        users = connection.search('ou=users,' + organization_dn, "(objectclass=*)", attributes=ALL_ATTRIBUTES)
        users = connection.response_to_json(users)
        users = json.loads(users)
    except Exception as e:
        logger.exception("Exception while retrieving LDAP information for users: %s" % e)
        raise RuntimeError("Exception while retrieving LDAP information for users: %s" % e)
    logger.info("LDAP information for users successfully retrieved")

    # Retrieve roles:
    try:
        logger.info("Trying to retrieve LDAP information for roles...")
        roles = connection.search('ou=roles,' + organization_dn, "(objectclass=*)", attributes=ALL_ATTRIBUTES)
        roles = connection.response_to_json(roles)
        roles = json.loads(roles)
    except Exception as e:
        logger.exception("Exception while retrieving LDAP information for roles: %s" % e)
        raise RuntimeError("Exception while retrieving LDAP information for roles: %s" % e)
    logger.info("LDAP information for roles successfully retrieved")

    # Retrieve groups:
    try:
        logger.info("Trying to retrieve LDAP information for groups...")
        groups = connection.search('ou=groups,' + organization_dn, "(objectclass=*)", attributes=ALL_ATTRIBUTES)
        groups = connection.response_to_json(groups)
        groups = json.loads(groups)
    except Exception as e:
        logger.exception("Exception while retrieving LDAP information for groups: %s" % e)
        raise RuntimeError("Exception while retrieving LDAP information for groups: %s" % e)
    logger.info("LDAP information for groups successfully retrieved")

    # Retrieve organizations:
    try:
        logger.info("Trying to retrieve LDAP information for organizations...")
        orgs = connection.search(organization_dn, "(objectclass=organization)", attributes=ALL_ATTRIBUTES)
        orgs = connection.response_to_json(orgs)
        orgs = json.loads(orgs)
    except Exception as e:
        logger.exception("Exception while retrieving LDAP information for organizations: %s" % e)
        raise RuntimeError("Exception while retrieving LDAP information for organizations: %s" % e)
    logger.info("LDAP information for organizations successfully retrieved")

    logger.info("LDAP information retrieved")

    return users, roles, groups, orgs

def generate_json(users, roles, groups, orgs, organization_dn) -> dict:
    """
    Processes every individual JSON object, passed as arguments, and generates a single
    JSON object with the LDAP information.
    """
    logger.info("Generating JSON object with LDAP information...")

    ldap_json = {}
    ldap_json["users"] = []
    ldap_json["roles"] = []
    ldap_json["groups"] = []
    ldap_json["organizations"] = []
    ldap_json["memberships"] = []
    
    # -- Users --
    for entry in range(1, len(users["entries"])):
        user = {}
        user["dn"] = users["entries"][entry]["dn"]
        user["attributes"] = {}
        for raw_attribute in users["entries"][entry]["raw"]:
            if (raw_attribute == 'objectClass'):
                user["attributes"][raw_attribute] = users["entries"][entry]["raw"][raw_attribute]
            else:
                user["attributes"][raw_attribute] = users["entries"][entry]["raw"][raw_attribute][0]    
        ldap_json["users"].append(user)

    # -- Roles --
    for entry in range(1, len(roles["entries"])):
        role = {}
        role["dn"] = roles["entries"][entry]["dn"]
        role["attributes"] = {}
        for raw_attribute in roles["entries"][entry]["raw"]:
            if (raw_attribute == 'objectClass') or (raw_attribute == 'memberUid'):
                role["attributes"][raw_attribute] = roles["entries"][entry]["raw"][raw_attribute]
                # Memberships generation:
                if (raw_attribute == 'memberUid'):
                    for memberUid in roles["entries"][entry]["raw"]["memberUid"]:
                        membership = {}
                        membership["memberUid"] = memberUid
                        membership["role_cn"] = roles["entries"][entry]["raw"]["cn"][0]
                        membership["organization_dn"] = organization_dn
                        ldap_json["memberships"].append(membership)
            else:
                role["attributes"][raw_attribute] = roles["entries"][entry]["raw"][raw_attribute][0]                
        ldap_json["roles"].append(role)

    # -- Groups --
    for entry in range(1, len(groups["entries"])):
        group = {}
        group["dn"] = groups["entries"][entry]["dn"]
        group["attributes"] = {}
        for raw_attribute in groups["entries"][entry]["raw"]:
            if (raw_attribute == 'objectClass') or (raw_attribute == 'memberUid'):
                group["attributes"][raw_attribute] = groups["entries"][entry]["raw"][raw_attribute]
            else:
                group["attributes"][raw_attribute] = groups["entries"][entry]["raw"][raw_attribute][0]                
        ldap_json["groups"].append(group)

    # -- Organizations --
    for entry in range(0, len(orgs["entries"])):
        org = {}
        org["dn"] = orgs["entries"][entry]["dn"]
        org["attributes"] = {}
        for raw_attribute in orgs["entries"][entry]["raw"]:
            if (raw_attribute == 'objectClass'):
                org["attributes"][raw_attribute] = orgs["entries"][entry]["raw"][raw_attribute]
            else:
                org["attributes"][raw_attribute] = orgs["entries"][entry]["raw"][raw_attribute][0]                
        ldap_json["organizations"].append(org)
    
    logger.info("JSON object generated")
    
    return ldap_json

def output_to_kafka(kafka_server: str, kafka_topic: str, ldap_json: dict) -> None:
    """
    Outputs the resulting JSON with the LDAP information to a Kafka topic, if the corresponding
    configuration directives are set.
    """
    logger.info("Trying to write output to the specified Kafka topic...")
    
    try:
        producer = KafkaProducer(bootstrap_servers=[kafka_server])
        producer.send(kafka_topic, value=json.dumps(ldap_json, indent=4).encode("utf-8"))
        producer.flush()
        producer.close()
    except Exception as e:
        logger.exception("Error while trying to write output to the specified Kafka topic: %s" % e)
        raise RuntimeError("Error while trying to write output to the specified Kafka topic: %s" % e)

    logger.info("Output successfully written to Kafka")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application started")

    # Check configuration file
    check_config(config=config)

    yield

    logger.info("Application finished")

## -- END DEFINITION OF AUXILIARY FUNCTIONS -- ##

## -- BEGIN MAIN CODE -- ##

app = FastAPI(
    lifespan=lifespan,
    title=__name__ + " - REST API",
    version=__version__
)

@app.get("/ldap.json")
async def get_ldap_information():
    logger.info("Received GET request to /ldap.json")

    # Retrieve values related with LDAP from configuration directives.
    organization_dn = config["ldap.general"]["organization_dn"]

    server_endpoint = config["ldap.connection"]["server_endpoint"]
    use_ssl = config["ldap.connection"].getboolean("use_ssl")
    user = config["ldap.connection"]["user"]
    password = config["ldap.connection"]["password"]
    max_retries = config["ldap.connection"].getint("max_retries")
    timeout = config["ldap.connection"].getint("max_retries")

    # Instantiate the representation of the LDAP server.
    server = Server(host=server_endpoint, use_ssl=use_ssl, get_info=ALL)

    # Try to establish the connection with the LDAP server.
    connection = establish_connection(server=server, user=user, password=password, max_retries=max_retries, timeout=timeout)

    # Retrieve LDAP information for users, roles, groups and organizations.
    users, roles, groups, orgs = retrieve_information(connection=connection, organization_dn=organization_dn)

    # Close the connection with the LDAP server.
    logger.info("Closing the connection with the LDAP server...")
    connection.unbind()
    logger.info("Connection successfully closed")

    # Generate the JSON object with LDAP information.
    ldap_json = generate_json(users=users, roles=roles, groups=groups, orgs=orgs, organization_dn=organization_dn)

    # If the directive "use_kafka" in the configuration file is set to True, the JSON object is written to
    # a Kafka topic, given its name and the server to use.
    if "kafka_server" in config["output"] and "kafka_topic" in config["output"]:
        kafka_server = config["output"]["kafka_server"]
        kafka_topic = config["output"]["kafka_topic"]
        output_to_kafka(kafka_server=kafka_server,
                        kafka_topic=kafka_topic,
                        ldap_json=ldap_json)

    logger.info("Returning JSON with LDAP data...")

    return ldap_json

## -- END MAIN CODE -- ##

