#!/bin/bash

# Delete configmap.
kubectl delete configmap aeros-ldap-collector-config

# Delete deployment.
kubectl delete -f aeros-ldap-collector.yaml
