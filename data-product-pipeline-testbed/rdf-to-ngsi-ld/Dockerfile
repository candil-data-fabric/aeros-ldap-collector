# aerOS - RDF to NGSI-LD Translator
# author: joseignacio.carretero <joseignacio.carretero@fiware.org>

# Initial stage: Copy repository and install PIP requirements
FROM python:3.11-alpine as initial-stage

ARG PROJECT=aeros
ARG COMPONENT=rdf-to-ngsi-ld
ARG VERSION=develop
ARG INSTALLATION_PATH=/opt/${PROJECT}/${COMPONENT}

RUN apk add --no-cache --virtual .build-deps gcc musl-dev linux-headers libffi-dev cargo openssl-dev

RUN mkdir -p ${INSTALLATION_PATH}
COPY . ${INSTALLATION_PATH}
RUN cp ${INSTALLATION_PATH}/requirements.txt /requirements.txt
RUN pip install --prefix=${INSTALLATION_PATH} -r /requirements.txt && chmod +x ${INSTALLATION_PATH}/main.py || true

# Final stage
# FROM python:3.11-bookworm as final-stage
FROM python:3.11-alpine as final-stage

ARG PROJECT=aeros
ARG COMPONENT=rdf-to-ngsi-ld
ARG VERSION=develop
ARG INSTALLATION_PATH=/opt/${PROJECT}/${COMPONENT}

LABEL maintainer="joseignacio.carretero@fiware.org"
LABEL description="RDF to NGSI-LD Translator built with Python version 3.11 on Alpine Linux"
LABEL version=${VERSION}

RUN mkdir -p ${INSTALLATION_PATH}

COPY --from=initial-stage ${INSTALLATION_PATH} /usr/local

# COPY settings/${VERSION}/config.ini ${INSTALLATION_PATH}/
# COPY settings/${VERSION}/.env ${INSTALLATION_PATH}/

WORKDIR ${INSTALLATION_PATH}

# EXECUTION: python main.py --from-kafka --to-ngsild-broker
ENTRYPOINT ["./main.py", "--from-kafka", "--to-ngsild-broker"]
