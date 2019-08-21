# Use a LTS Ubuntu version as parent image
FROM ubuntu:18.04

# Install dependencies (Python and postgresql)
RUN apt-get update && apt-get install --no-install-recommends -y \
    python3.6 \
    python3-dev \
    python3-pip \
    python3-setuptools \
    postgresql \
    postgresql-client \
    postgresql-contrib \
    libpq-dev \
    gcc
    
# Install chado-tools
RUN pip3 install wheel && pip3 install chado-tools

# Define the default command
CMD "chado -h"

#Metadata
LABEL maintainer "path-help@sanger.ac.uk"
