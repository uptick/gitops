FROM python:rc-alpine

# Install kubectl and dependencies.
RUN apk add -U openssl curl tar gzip bash ca-certificates && \
wget -q -O /etc/apk/keys/sgerrand.rsa.pub https://raw.githubusercontent.com/sgerrand/alpine-pkg-glibc/master/sgerrand.rsa.pub && \
wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.23-r3/glibc-2.23-r3.apk && \
apk add glibc-2.23-r3.apk && \
rm glibc-2.23-r3.apk
RUN curl -L -o /usr/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/v1.8.0/bin/linux/amd64/kubectl && \
chmod +x /usr/bin/kubectl && \
kubectl version --client

RUN mkdir /app
COPY requirements.txt /app
RUN    apk add --no-cache --update --virtual build-dependencies \
        git wget postgresql-dev g++ make libffi-dev \
    && pip install -r /app/requirements.txt \
    && apk del build-dependencies \
    && rm -rf /var/lib/apt/lists/* /root/.cache
COPY main.py /app/

CMD ["python", "/app/main.py"]
