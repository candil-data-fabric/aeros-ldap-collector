# RDF to NGSI-LD Translator

This Python project implements a generic translator from RDF to NGSI-LD.

The work takes inspiration from
[rdflib](https://rdflib.readthedocs.io/en/stable/index.html) plugins that store
RDF data in backends like Neo4j (https://github.com/neo4j-labs/rdflib-neo4j).

In this sense, this project provides an rdflib plugin where an NGSI-LD Context
Broker works as the storage backend for RDF data. Additionally, the translator
supports the ingestion of streams of RDF data via Kafka.

## Translation Rules

The following set of rules are applied to translate the RDF data model (triples)
into the NGSI-LD data model (property graph):

- **Subject**: Maps to an NGSI-LD Entity. The URI of the subject in
  the RDF triple is the URI of the NGSI-LD Entity.

  > :warning: This approach does not follow the convention recommended by
  > ETSI CIM, which goes "urn:ngsi-ld:\<entity-type>:\<identifier>".
  > The reason for doing this is to facilitate interoperability between RDF and
  > NGSI-LD.

- **Predicate**:
  - `a` or `rdf:type` predicate maps to the NGSI-LD Entity Type. For example:
  the RDF triple `<http://example.org/people/Bob> a foaf:Person` translates
  into an NGSI-LD Entity of `foaf:Person` type, and URI
  `http://example.org/people/Bob`.

  - **RDF Datatype property** maps to an NGSI-LD Property. A special treatment
  is required when the literal of the predicate uses `xsd:datetime`.
  In this case the resulting NGSI-LD Property must follow the special format:

    ```json
        "myProperty": {
            "type": "Property", "value": {
                "@type": "DateTime",
                "@value": "2018-12-04T12:00:00Z"
            }
        }
    ```

  - **RDF Object property** maps to an NGSI-LD Relationship. The target of the
  Relationship is the URI of the object in the RDF triple.

- **Namespaces**: There is no need to create specific `@context` for translating
  to NGSI-LD. The resulting NGSI-LD Entity can just used expanded the URIs.
  This approach is easier to maintain as avoids maintaining `@context` files.

  Optionally, If the ingested RDF data includes a definition of namespaces
  with prefixes, then this information could be used to generate the
  `@context` for the translated NGSI-LD Entity. The resulting `@context` can be
  send along the NGSI-LD payload or stored elsewhere and reference
  via Link header. The selected approach will depend on the use case
  andthe developer's implementation.

## Translation Modes

The translator could be configured to expect `batches` of RDF data, instead of
`streaming` events. In batching mode, the translator can analyze all RDF triples
for the same subject, bundle the datatype and object properties, and ppython main.py --to-kafka-demo tests/examples/simple-sample-relationship.ttl tests/examples/containerlab-graph.nt333ºroduce
a complete NGSI-LD Entity with a set of Properties and Relationships.
This approach can improve performance as less NGSI-LD requests are sent
to create the Entities in the Context Broker.

## Installation
### Prerequisites
Python 3.10+ is required. Some programming constructs from Python 3.10 has been used in the project. At least Python 3.11 is recommended.

### Installation in our system, with virtual environment
Creating a Python Virtual Environment is quite recommendable `virtualenv ~/.venv/rdf2ngsild` and activating the virtual environment before doing anything with `source ~/.ven/rdf2ngsild/bin/activate`. Then we can proceed with installation:

```
git clone https://gitlab.aeros-project.eu/wp4/t4.2/rdf-to-ngsi-ld.git
cd rdf-to-ngsi-ld
pip install -r requirements.txt
```

### Docker installation
The Docker image can be built using the following command:

```bash
sudo docker image build -t aeros-project/rdf-to-ngsi-ld:latest .
```

## Usage
The application reads RDF triples from a Kafka topic and converts them to NGSI-LD, writing the output to an NGSI-LD Context Broker (like Orion-LD):

```bash
python main.py --from-kafka --to-ngsild-broker
```

## Configuration file
This is an example of a configuration file:

```ini
# Default configurations
[default]
## A list for the context - Just formatted like an array. This is to set the default context
context = ["https://fiware.github.io/data-models/context.jsonld"]

## context = ["https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"]

# Transformations to URN
[urn-transform]
## urn = std_urn_name - If this is the value, the id of the enties will be calculated from
##                      the URI value of RDF's file, something similar to this: 
##                      id = urn:xxx:typeentity:identity
## Any other value will not transform anything
urn = std_urn_name_no

[type-transform]
## urn = std_type_name - If this is the value, the type will be calculated removing anything
##                       before the last ":" character. It can be other things and the name
##                       will be left as URI.
## urn = std_default_type - Sets default value according to parameter default_type_value
##
## urn = std_type_default
urn = std_type_default

retype_function = std_name_only
default_type_value = rdfs:resource

[encode-transform]
# Encode or not encode the ID of the of the entity (used mainly for patches) -- If we use a 
# URL as ID for the entity in Orion-ld, we need to encode it in order to put the ID in
# the URL as a paramter for the query.
#
# If the encoder here is as shown, then the encoder will encode the ID
# encoder = encode_url_as_http    
#
# If we don't need to encode, we can use (this is the default behaviour):
# encoder = encode_url_not
#
encoder = encode_url_as_http

[kafka-client]
## Cofiguration for the Kafka reader. It will connect to a topic in a server
servers = localhost:19092
topic = rdf-topic

# Timeout of reader. -1 means infinite.
reader_timeout = -1

[brokerld]
### NGSI-LD Broker basic URL to connect to when data is sent to NGSI-LD Broker.
url = http://localhost:1026
pool_size = 1

[kafka-demo]
## This is for testing purposes. It is used with the --to-kafka parameter and it will
## say how many messages are going to be sent, and the waiting time between them.

## Max number of messages to be sent (<0 means infinity)
max_messages_sent = 10000

## thread.sleep between messages. It will send a message every... seconds
wait_between_messages = 0
```


### Testing purposes
For testing purposes, you could write some data to the Kafka topic where the application reads from. For example:

```bash
python main.py --to-kafka-demo tests/examples/simple-sample-relationship.ttl tests/examples/containerlab-graph.nt
```
