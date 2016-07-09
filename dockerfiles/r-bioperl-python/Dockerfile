# Script runner base image
#
# VERSION       0.3
# This Dockerfile is the base system for executing scripts with the docker scriptrunner.

FROM mvdbeek/scriptrunner

MAINTAINER Marius van den Beek, m.vandenbeek@gmail.com

USER galaxy
RUN bash -c ". activate default && \
    conda install -y ncurses biopython perl-bioperl bedtools bioconductor-deseq2 bioconductor-edger numpy scipy"
USER root
RUN chown -R galaxy:users /home/galaxy && chmod g=rwx /home/galaxy
