#!/usr/bin/env bash
LOGIN="docker login -e=$DOCKER_EMAIL -u=$DOCKER_USERNAME -p=$DOCKER_PASSWORD" && \
$LOGIN || (sleep 5s && $LOGIN || echo "login failed twice, quitting" && exit 1) && \
docker push artbio/scriptrunner || (sleep 5s && docker push artbio/scriptrunner || echo "push failed twice, quitting" && exit 1) && \
docker push artbio/scriptrunner-r-bioperl-python || (sleep 5s && docker push artbio/scriptrunner-r-bioperl-python || echo "push failed twice, quitting" && exit 1)
