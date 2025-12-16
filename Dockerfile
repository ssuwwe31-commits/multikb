FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHON_VERSION=3.11.14 \
    APP_HOME=/opt/multikb-knowledge-backend

# System packages required to build Python and common binary wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libffi-dev \
    liblzma-dev \
    uuid-dev \
    wget \
    ca-certificates \
    curl \
    git \
 && rm -rf /var/lib/apt/lists/*

# Build and install CPython 3.11.14 from source
RUN cd /usr/src \
 && wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz \
 && tar xzf Python-${PYTHON_VERSION}.tgz \
 && cd Python-${PYTHON_VERSION} \
 && ./configure --enable-optimizations \
 && make -j"$(nproc)" \
 && make altinstall \
 && cd / \
 && rm -rf /usr/src/Python-${PYTHON_VERSION} /usr/src/Python-${PYTHON_VERSION}.tgz

# Install pip for the new interpreter
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Optionally make python/pip aliases (uncomment if desired)
# RUN ln -s /usr/local/bin/python3.11 /usr/local/bin/python && \
#     ln -s /usr/local/bin/pip3.11 /usr/local/bin/pip

WORKDIR ${APP_HOME}

# Install Python dependencies first to leverage Docker layer caching
COPY requirements.txt ${APP_HOME}/
RUN python3.11 -m pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . ${APP_HOME}

# Default command (adjust to your entrypoint needs)
CMD ["python3.11", "app.py"]

