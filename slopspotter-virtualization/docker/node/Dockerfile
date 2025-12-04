FROM node:18-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends strace && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /scan
COPY runner.js /scan/runner.js

ENTRYPOINT ["node", "/scan/runner.js"]
