# Script runner base image
#
# VERSION       0.3
# This Dockerfile is the base system for executing scripts with the docker scriptrunner.

FROM toolshed/requirements

MAINTAINER Marius van den Beek, m.vandenbeek@gmail.com

# make sure the package repository is up to date
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get -qq update

# Install all requirements that are recommend by the Galaxy project
RUN apt-get install -y libfreetype6-dev wget curl \
libcurl4-openssl-dev libssl-dev libreadline-dev libxml2-dev liblzma-dev \
libpcre3-dev libbz2-dev

RUN adduser galaxy -u 1450
USER galaxy
ENV CONDA_PREFIX="/homa/galaxy/conda" \
    VENV="/homa/galaxy/.venv/bin/activate" \
    CONDA=CONDA_PREFIX/bin/conda

RUN . "$VENV" && \
    pip install planemo && \
    planemo conda_init --conda_prefix "$CONDA_PREFIX" && \
    "$CONDA" create -y -q -c bioconda --name iuc_conda samtools=0.1.19 bcftools &&
    . activate iuc_conda && \
    "$CONDA" config --add channels r && \
    "$CONDA" config --add channels bioconda && \
    "$CONDA" config --add channels iuc