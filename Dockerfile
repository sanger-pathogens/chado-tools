# Use a LTS Ubuntu version as parent image
FROM ubuntu:18.04
ARG DEBIAN_FRONTEND=noninteractive
ARG PYTHONWARNINGS="ignore:Unverified HTTPS request"

# Install general dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
    git \
    python \
    python3-dev \
    python3-setuptools \
    python3-pip \
    postgresql \
    postgresql-client \
    postgresql-contrib

# Install python dependencies 
RUN pip3 install --trusted-host pypi.python.org --upgrade pip
RUN pip3 install certifi
RUN pip3 install wheel \
  && pip3 install nose \
  && pip3 install pyyaml \
  && pip3 install psycopg2-binary

# Set up PostgreSQL
RUN update-rc.d postgresql enable
USER postgres
RUN service postgresql start \
  && psql --command "CREATE USER docker WITH SUPERUSER PASSWORD 'docker';" \
  && createdb -O docker docker
  
# Adjust PostgreSQL configuration so that remote connections to the database are possible.
RUN PSQL_VERSION=$(ls /etc/postgresql/) \
  && echo "host all  all    0.0.0.0/0  md5" >> /etc/postgresql/$PSQL_VERSION/main/pg_hba.conf \
  && echo "listen_addresses='*'" >> /etc/postgresql/$PSQL_VERSION/main/postgresql.conf

# Expose the PostgreSQL port
EXPOSE 5432
  
# Download and setup the application
USER root
RUN service postgresql start \
  && git clone https://github.com/sanger-pathogens/chado-tools.git \
  && cd chado-tools \
  && echo "database: postgres\nhost:     localhost\nport:     5432\nuser:     docker\npassword: docker\n" > pychado/data/defaultDatabase.yml \
  && python3 setup.py test \
  && python3 setup.py install

# Define the command with which the application is run
CMD chado
