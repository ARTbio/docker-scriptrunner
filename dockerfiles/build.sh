#!/usr/bin/env bash
cd "${0%/*}"
docker build -t artbio/scriptrunner scriptrunner && \
docker build -t artbio/scriptrunner-r-bioperl-python r-bioperl-python
