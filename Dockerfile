FROM python:3.9-slim

##
## Install kubectl and dependencies.
##
# RUN apk add -U openssl curl tar gzip bash ca-certificates && \
# wget -q -O /etc/apk/keys/sgerrand.rsa.pub https://raw.githubusercontent.com/sgerrand/alpine-pkg-glibc/master/sgerrand.rsa.pub && \
# wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.23-r3/glibc-2.23-r3.apk && \
# apk add glibc-2.23-r3.apk && \
# rm glibc-2.23-r3.apk
# RUN curl -L -o /usr/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/v1.8.0/bin/linux/amd64/kubectl && \
# chmod +x /usr/bin/kubectl && \
# kubectl version --client
ENV KUBE_LATEST_VERSION v1.21.3
ENV HELM_VERSION v3.6.2
RUN apt-get update
RUN apt-get install wget ca-certificates bash git git-crypt -y --no-install-recommends \
    && wget -q https://storage.googleapis.com/kubernetes-release/release/${KUBE_LATEST_VERSION}/bin/linux/amd64/kubectl -O /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl \
    && wget -q https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz -O - | tar -xzO linux-amd64/helm > /usr/local/bin/helm \
    && chmod +x /usr/local/bin/helm \
    && apt-get clean \
    && apt-get -y autoremove \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/ \
ENV SHELL=/bin/bash

##
## Install dependencies and copy GitOps server.
##

WORKDIR /app

RUN pip3 install poetry
COPY pyproject.toml poetry.lock /app/

# Install dependencies
RUN poetry install -E server --no-dev

COPY cluster.key /app/
COPY gitops /app/gitops/
COPY gitops_server /app/gitops_server

ENV GIT_CRYPT_KEY_FILE=/app/cluster.key
ENV PYTHONPATH="$PYTHONPATH:/app"
ENV ACCESS_LOG=""


CMD ["poetry", "run", "uvicorn", "--host", "0.0.0.0", "--port", "8000", "gitops_server.main:app"]
