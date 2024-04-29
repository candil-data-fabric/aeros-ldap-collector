#!/bin/bash

# Create configmap from configuration file.
kubectl create configmap aeros-ldap-collector-config --from-file=configmap/config.ini

# Create deployment.
kubectl apply -f aeros-ldap-collector.yaml
