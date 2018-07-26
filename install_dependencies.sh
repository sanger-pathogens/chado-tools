#!/bin/bash

# Install PostgreSQL
sudo apt-get update
sudo apt-get install postgresql postgresql-client postgresql-contrib

# Setup PostgreSQL and create a new user
sudo update-rc.d postgresql enable
service postgresql start 
su - postgres
psql --command "CREATE USER chado_user WITH SUPERUSER PASSWORD 'chado_pw';" \
createdb -O chado_user chado_user
