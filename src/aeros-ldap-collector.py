## -- BEGIN IMPORT STATEMENTS -- ##

import argparse
import configparser
import json
from kafka import KafkaProducer
from ldap3 import Server, Connection, ALL, ALL_ATTRIBUTES
import logging
import os

## -- END IMPORT STATEMENTS -- ##

## -- BEGIN CONSTANTS DECLARATION -- ##

VERSION = "0.0.1"

## -- END CONSTANTS DECLARATION -- ##

## -- BEGIN DEFINITION OF AUXILIARY FUNCTIONS -- ##

def parse_arguments():
    """
    Parses invocation arguments.
    """

    parser = argparse.ArgumentParser(
        description="LDAP collector based on the ldap3 Python library for the aerOS Project",
        prog="python3 aeros-ldap-collector.py",
        argument_default=argparse.SUPPRESS
    )

    parser.add_argument("-c", "--config", type=str, help="Path to the configuration file.")
    parser.add_argument("-v", "--version", action="version", version="aerOS LDAP collector - Version " + VERSION)

    return parser.parse_args()

def load_config():
    """
    Loads configuration directives from the configuration file.
    """
    arguments = parse_arguments()

    config = configparser.ConfigParser()
    config.read(arguments.config)

    return config

def configure_logging():
    """
    Configures the logger for this application.
    """
    logger = logging.getLogger(name="aerOS LDAP collector")
    return logger

def retrieve_information(connection: Connection, organization_dn: str):
    """
    Retrieves LDAP information for users, roles, groups and organizations, and returns it JSON objects.
    """
    # Retrieve users:
    users = connection.search('ou=users,' + organization_dn, "(objectclass=*)", attributes=ALL_ATTRIBUTES)
    users = connection.response_to_json(users)
    users = json.loads(users)

    # Retrieve roles:
    roles = connection.search('ou=roles,' + organization_dn, "(objectclass=*)", attributes=ALL_ATTRIBUTES)
    roles = connection.response_to_json(roles)
    roles = json.loads(roles)

    # Retrieve groups:
    groups = connection.search('ou=groups,' + organization_dn, "(objectclass=*)", attributes=ALL_ATTRIBUTES)
    groups = connection.response_to_json(groups)
    groups = json.loads(groups)

    # Retrieve organizations:
    orgs = connection.search(organization_dn, "(objectclass=organization)", attributes=ALL_ATTRIBUTES)
    orgs = connection.response_to_json(orgs)
    orgs = json.loads(orgs)

    return users, roles, groups, orgs

def generate_json(users, roles, groups, orgs) -> str:
    """
    Processes every individual JSON object, passed as arguments, and generates a single
    JSON object with the LDAP information.
    """
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
    
    return json.dumps(ldap_json, indent=4)

def output_to_file(output_filename: str, ldap_json: str) -> None:
    """
    Outputs the resulting JSON with the LDAP information to a file, if the corresponding
    configuration directive is set.
    """
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    with open(output_filename, "w") as file:
        file.write(ldap_json)
        file.close()

def output_to_kafka(kafka_server: str, kafka_topic: str, ldap_json: str) -> None:
    """
    Outputs the resulting JSON with the LDAP information to a Kafka topic, if the corresponding
    configuration directives are set.
    """
    producer = KafkaProducer(bootstrap_servers=[kafka_server])
    producer.send(kafka_topic, value=ldap_json.encode("utf-8"))
    producer.flush()
    producer.close()

## -- END DEFINITION OF AUXILIARY FUNCTIONS -- ##

## -- BEGIN MAIN CODE -- ##

logger = configure_logging()

logger.info("Application started")

logger.info("Trying to read configuration directives from the configuration file...")
config = load_config()
logger.info("Configuration directives read")

organization_dn = config["ldap.general"]["organization_dn"]

server_endpoint = config["ldap.connection"]["server_endpoint"]
use_ssl = bool(config["ldap.connection"]["use_ssl"])

server = Server(host=server_endpoint,
                use_ssl=use_ssl,
                get_info=ALL)

user = config["ldap.connection"]["user"]
password = config["ldap.connection"]["password"]

connection = Connection(server=server, user=user, password=password, auto_bind=True)

users, roles, groups, orgs = retrieve_information(connection=connection, organization_dn=organization_dn)

connection.unbind()

ldap_json = generate_json(users=users, roles=roles, groups=groups, orgs=orgs)

if "file" in config["output"]:
    output_to_file(output_filename=config["output"]["file"], ldap_json=ldap_json)
if "kafka_server" in config["output"] and "kafka_topic" in config["output"]:
    output_to_kafka(kafka_server=config["output"]["kafka_server"],
                    kafka_topic=config["output"]["kafka_topic"],
                    ldap_json=ldap_json)

## -- END MAIN CODE -- ##
