#!/usr/bin/env bash
docker build -t artbio/scriptrunner scriptrunner && \
docker build -t artbio/scriptrunner-r-bioperl-python r-bioperl-python
