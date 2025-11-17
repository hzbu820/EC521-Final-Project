FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    strace \
    tcpdump \
    iptables \
    iproute2 \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Create directories
RUN mkdir -p /app/runner/
RUN mkdir -p /app/tests/

# Install Python dependencies (use pip, not apk)
RUN pip install --no-cache-dir \
    pyyaml \
    psutil \
    watchdog

# Copy runner scripts
COPY runner/ /app/runner/
COPY tests/ /app/tests/

# Create directories for logs and reports
RUN mkdir -p /app/logs /app/reports

# Set up limited user for running untrusted code
RUN useradd -m -s /bin/bash sandbox_user && \
    chown -R sandbox_user:sandbox_user /app

# Default command
CMD ["/bin/bash"]
