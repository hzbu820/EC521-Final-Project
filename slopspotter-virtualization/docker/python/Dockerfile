FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends strace && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /scan
COPY runner.py /scan/runner.py

ENTRYPOINT ["python", "/scan/runner.py"]
