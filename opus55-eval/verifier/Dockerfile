FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends default-jre-headless && rm -rf /var/lib/apt/lists/*
COPY . /tests/
RUN mkdir -p /workspace/output /logs/verifier
WORKDIR /tests
