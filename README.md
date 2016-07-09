[![Build Status](https://travis-ci.org/ARTbio/docker-scriptrunner.svg?branch=master)](https://travis-ci.org/ARTbio/docker-scriptrunner)

You need to have docker 
Docker scriptrunner for galaxy
-----------------------------

This is a [galaxy](https://github.com/galaxyproject/galaxy) tool that allows
users to submit random scripts.
You can install it on your galaxy server from the [galaxy toolshed] (https://toolshed.g2.bx.psu.edu/view/mvdbeek/docker_scriptrunner/).


This tool is heavily inspired by Ross Lazarus' tool factory
(https://www.ncbi.nlm.nih.gov/pubmed/23024011), but removes the ability to
create galaxy tools. (If you are looking at creating galaxy tools, you may want 
to use [planemo](https://planemo.readthedocs.io/en/latest/)).


You need to have docker installed on any machine that can run
galaxy jobs, or route this tool to a dedicated docker host
in galaxy's job_conf.xml. Note that the tool itself talks
to the docker daemon and bypasses galaxy's docker configuration.
Making use of galaxy's docker capabilities is on the roadmap.


The tool comes with two docker images that can be easily extended.
"artbio/scriptrunner" is a base image, that has very few dependencies installed.
You can extend the image by following the example in the dockerfiles/r-bioperl-python
folder.


All security relies on docker; the container only mounts those files that the user
has selected as input files, and the script itself drops privileged inside
the container. This should be secure, but caution should be taken on public servers.
By default the container has networking enabled, so make sure your firewall rules
forbid traffic to the local network.
