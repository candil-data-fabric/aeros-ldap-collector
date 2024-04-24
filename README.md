# aerOS LDAP Collector
LDAP collector based on the `ldap3` Python library for the aerOS Project.

**Current version:** 1.1.2 (April 24th, 2024).

It connects to an LDAP server, retrieves information of users, roles, groups and organizations and generates a JSON object which can be used later by Morph-KGC to generate RDF triples given the appropriate mappings file. An example of this output JSON file is available [here](files/example_ldap.json).

The YARRRML mappings file can also be found [here](files/mappings.yaml). The definition of these mappings is done given the aerOS Ontology definition, which diagram is included below:

<img src="docs/aerOS-continuum-ontology.png" width="1200">

The generation and retrieval of the JSON object is requested via a REST API method (`HTTP GET /ldap.json`) that the collector exposes. A sequence diagram that describes the general behaviour is included below:

![](docs/sequence_diagram.png)

## Building the Docker image
The collector is meant to be run as a Docker container, hence a [`Dockerfile`](Dockerfile) is provided. To build the image, simply run the following command:

```bash
$ sudo docker build -t aeros-project/ldap-collector:latest .
```

**NOTE:** The HTTP server of the collector will run on port 63300 (TCP). It can be changed by modifying the [`Dockerfile`](Dockerfile).

## Running the collector

A Helm Chart for running the collector as a Kubernetes application is in the works.

The collector is configured using an [`INI` file](https://en.wikipedia.org/wiki/INI_file). This file must always be placed in the following directory of the container (when run; use a volume to mount the file): `/aeros-ldap-collector/files/config.ini`. An example file is available [here](files/config.ini), although the structure of the file is the following:

```ini
; Configuration file for aerOS LDAP Collector.

; Default configuration directives:
[DEFAULT]
; No default directives are used as of now.

; (MANDATORY) General directives for the LDAP database:
[ldap.general]
; (MANDATORY) organization_dn (String): DN of the organization which information is to be retrieved.
organization_dn = <value>

; (MANDATORY) Directives for establishing a connection with the LDAP server:
[ldap.connection]
; (MANDATORY) server_endpoint (String): URI where the server is listening for incoming connections or requests.
; FORMAT: ldap(s)://<ip_or_fqdn>:<port>
; LDAP (unencrypted) port is 389. LDAPS (encrypted) port is 636.
server_endpoint = <value>

; (MANDATORY) use_ssl (Boolean): defines whether or not to use SSL for the connection with the server.
; Valid values are True or False.
use_ssl = <value>

; (MANDATORY) user (String): defines the DN of the LDAP user for connecting and retrieving information.
user = <value>

; (MANDATORY) password (String): password of the LDAP user defined above.
password = <value>

; (MANDATORY) max_retries (Integer): defines the maximum number of times the client will try to establish
; a connection with the server.
max_retries = <value>

; (MANDATORY) timeout (Integer): defines the time (in seconds) to wait between retries while trying to establish
; a connection with the server.
timeout = <value>

; (MANDATORY) Additional directives for outputting the JSON object that contains the LDAP information:
[output]

; (OPTIONAL) kafka_server (String): defines the socket where the Kafka server is reachable.
; FORMAT: <ip_or_fqdn>:<port>.
; It is MANDATORY if you wish to use Kafka as the desired output option.
kafka_server = <value>

; (OPTIONAL) kafka_topic (String): defines the topic to use for writing the resulting JSON object.
; It is MANDATORY if you wish to use Kafka as the desired output option.
kafka_topic = <value>
```
