FROM python:3.7-alpine

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
ENV KUBE_LATEST_VERSION v1.12.7
ENV HELM_VERSION v2.13.1
RUN    apk add --no-cache ca-certificates bash git \
    && wget -q https://storage.googleapis.com/kubernetes-release/release/${KUBE_LATEST_VERSION}/bin/linux/amd64/kubectl -O /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl \
    && wget -q http://storage.googleapis.com/kubernetes-helm/helm-${HELM_VERSION}-linux-amd64.tar.gz -O - | tar -xzO linux-amd64/helm > /usr/local/bin/helm \
    && chmod +x /usr/local/bin/helm

##
## Install git-crypt.
##
ENV GITCRYPT_VERSION 0.6.0
RUN    apk add --no-cache --update --virtual build-dependencies \
        make openssl-dev \
    && apk add --update \
        openssl g++ \
    && wget -q https://github.com/AGWA/git-crypt/archive/debian/$GITCRYPT_VERSION.tar.gz -O - | tar zxv -C /var/tmp \
    && cd /var/tmp/git-crypt-debian \
    && make \
    && make install PREFIX=/usr/local \
    && rm -rf /var/tmp/git-crypt-debian \
    && apk del build-dependencies \
    && rm -rf /var/lib/apt/lists/* /root/.cache

##
## Install dependencies and copy GitOps server.
##
RUN mkdir -p /app
COPY requirements.txt /app
RUN    apk add --no-cache --update --virtual build-dependencies \
        git make libffi-dev \
    && pip install -r /app/requirements.txt \
    && apk del build-dependencies \
    && rm -rf /var/lib/apt/lists/* /root/.cache
COPY gitops_server /app/gitops_server
COPY tests /app/tests

ENV PYTHONPATH=/app:$PYTHONPATH
WORKDIR /app

CMD ["python", "/gitops_server"]
