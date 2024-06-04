# LDAP Collector - Dockerfile.

# The base image is Ubuntu 22.04 LTS ("jammy").
FROM ubuntu:jammy

# Some labels are defined to store metadata.
LABEL image_version="2.0.0"
LABEL app_version="1.1.3"
LABEL maintainer="David Martínez García"

# Variables to automatically install/update tzdata.
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Madrid

# Update base image with new packages.
RUN apt-get update && apt-get dist-upgrade -y && apt-get autoremove -y && apt-get autoclean

# Install some basic tools and dependencies.
RUN apt-get install -y --no-install-recommends bash python3 python3-pip openssl net-tools wget curl iputils-ping

# Install Python dependencies using PIP.
RUN python3 -m pip install ldap3 fastapi uvicorn

# Create application's directory and copy the script.
RUN mkdir -p /ldap-collector
COPY ./ldap_collector /ldap-collector/ldap_collector

# Switch to application's directory as main WORKDIR.
WORKDIR /ldap-collector

# Finally, the ENTRYPOINT is defined.
# The configuration file MUST be included in the invocation.
# Its path can be included as a command or by overriding this ENTRYPOINT.
ENTRYPOINT ["uvicorn", "ldap_collector.main:app", "--host", "0.0.0.0", "--port", "63300", "--reload"]
