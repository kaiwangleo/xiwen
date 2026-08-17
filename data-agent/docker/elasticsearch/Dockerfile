FROM docker.elastic.co/elasticsearch/elasticsearch:8.19.0

USER root
RUN elasticsearch-plugin install --batch \
    https://release.infinilabs.com/analysis-ik/stable/elasticsearch-analysis-ik-8.19.0.zip
USER elasticsearch
