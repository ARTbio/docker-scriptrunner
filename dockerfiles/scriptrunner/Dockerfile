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
RUN apt-get install -y --no-install-recommends imagemagick libfreetype6-dev wget curl \
libcurl4-openssl-dev libssl-dev libreadline-dev libxml2-dev liblzma-dev \
libpcre3-dev libbz2-dev libx11-dev 

RUN mkdir /var/home && \
    useradd galaxy --create-home --home-dir /home/galaxy  --uid 1450 && \
    chown -R galaxy:galaxy /home/galaxy/
USER galaxy
WORKDIR /home/galaxy
ENV CONDA_PREFIX="/home/galaxy/conda" \
    PATH="/home/galaxy/conda/envs/default/bin:/home/galaxy/conda/bin:$PATH"

RUN curl https://repo.continuum.io/miniconda/Miniconda-latest-Linux-x86_64.sh -L -o miniconda.sh 
RUN bash miniconda.sh -b -p "$CONDA_PREFIX" && rm miniconda.sh
RUN bash -c "conda create -y -q -c bioconda --name default samtools==0.1.19 bcftools && \
    conda config --add channels r && \
    conda config --add channels bioconda && \
    conda config --add channels iuc && \
    . activate default && \
    conda install ghostscript"
USER root
RUN chown -R galaxy:users /home/galaxy && \
    chmod g=rwx /home/galaxy && \
    usermod -G users galaxy
