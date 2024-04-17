## -- BEGIN IMPORT STATEMENTS -- ##

import configparser
import json
from kafka import KafkaProducer
from ldap3 import Server, Connection, ALL, ALL_ATTRIBUTES
import os
import sys

## -- END IMPORT STATEMENTS -- ##

## -- BEGIN DEFINITION OF AUXILIARY FUNCTIONS -- ##

def generate_json(users: str | bytes | bytearray,
                  roles: str | bytes | bytearray,
                  groups: str | bytes | bytearray,
                  orgs: str | bytes | bytearray) -> str:
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
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    with open(output_filename, "w") as file:
        file.write(ldap_json)
        file.close()

def output_to_kafka(kafka_server: str, kafka_topic: str, ldap_json: str) -> None:
    producer = KafkaProducer(bootstrap_servers=[kafka_server])
    producer.send(kafka_topic, value=ldap_json.encode("utf-8"))
    producer.flush()
    producer.close()

## -- END DEFINITION OF AUXILIARY FUNCTIONS -- ##

## -- BEGIN MAIN CODE -- ##

if len(sys.argv) != 2:
    print("ERROR: Incorrect number of arguments")
    print("Usage: python3 aeros-ldap-collector.py <path_to_config_file>")
    print("Example: python3 aeros-ldap-collector.py /aeros-ldap-collector/files/config.ini")
    sys.exit(1)
else:
    config_file_path = sys.argv[1]

config = configparser.ConfigParser()
config.read(config_file_path)

organization_dn = config["ldap.general"]["organization_dn"]

server_host = config["ldap.server"]["host"]
server_port = config["ldap.server"]["port"]
server_use_ssl = bool(config["ldap.server"]["use_ssl"])
server_get_info = config["ldap.server"]["get_info"]

server = Server(host=server_host,
                port=server_port,
                use_ssl=server_use_ssl,
                get_info=server_get_info)

connection_user = config["ldap.connection"]["user"]
connection_password = config["ldap.connection"]["password"]

connection = Connection(server=server, user=connection_user, password=connection_password, auto_bind=True)

# Retrieve users:
users = connection.search('ou=users' + organization_dn, "(objectclass=*)", attributes=ALL_ATTRIBUTES)
users = connection.response_to_json(users)

# Retrieve roles:
roles = connection.search('ou=roles' + organization_dn, "(objectclass=*)", attributes=ALL_ATTRIBUTES)
roles = connection.response_to_json(roles)

# Retrieve groups:
groups = connection.search('ou=groups' + organization_dn, "(objectclass=*)", attributes=ALL_ATTRIBUTES)
groups = connection.response_to_json(groups)

# Retrieve organizations:
orgs = connection.search(organization_dn, "(objectclass=organization)", attributes=ALL_ATTRIBUTES)
orgs = connection.response_to_json(orgs)

ldap_json = generate_json(users=users, roles=roles, groups=groups, orgs=orgs)

if "file" in config["output"]:
    output_to_file(output_filename=config["output"]["file"], ldap_json=ldap_json)
if "kafka_server" in config["output"] and "kafka_topic" in config["output"]:
    output_to_kafka(kafka_server=config["output"]["kafka_server"],
                    kafka_topic=config["output"]["kafka_topic"],
                    ldap_json=ldap_json)

## -- END MAIN CODE -- ##
