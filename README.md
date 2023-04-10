# Open Banking Archiver

[![Lint](https://github.com/sebcoetzee/open-banking-archiver/actions/workflows/lint.yaml/badge.svg)](https://github.com/sebcoetzee/open-banking-archiver/actions/workflows/lint.yaml)

Python-based application that requests Open Banking data from the Nordigen API and inserts it into a PostgreSQL database.

### Data Disclaimer

**IMPORTANT**: This project is built with the intention to archive my own personal bank transactions to a Postgres database. I am not liable for any data handling infringements that arise for the use of this software. There are strict laws that govern the use of financial data: please ensure that you comply with the laws if you intend to use this software.

### Usage

You can find the Docker image on [Docker Hub](https://hub.docker.com/repository/docker/sebcoetzee/open-banking-archiver/general). Docker is the easiest way to run the application in a server environment.

#### Database Migrations

The project uses [yoyo-migrations](https://ollycope.com/software/yoyo/latest/) in order to manage any database schema migrations for the underlying postgres database. In order to run the schema migrations, ensure that you have a Postgres database up and running with a user that has the appropriate superuser access. To run the migrations in Docker directly, run the following command:

```
docker run --rm -it \
    sebcoetzee/open-banking-archiver:latest \
    yoyo apply -p -b -d postgresql://<my_postgres_user>@<my_postgres_host>:<postgres_port>/<postgres_db_name> sql/
```

You will be prompted to enter the database password. The database migrations will then be applied.

#### Running in Docker

The easiest way to run the application is to run the Docker container directly. All the configuration options can be passed to the application as command-line arguments:

```
docker run --rm -it \
    -e NORDIGEN_SECRET_ID=my_secret_id \
    -e NORDIGEN_SECRET_KEY=my_secret_key \
    -e DB_HOST=my_postgres_host \
    -e DB_PORT=5432 \
    -e DB_USER=my_postgres_user \
    -e DB_PASSWORD=my_password \
    -e DB_NAME=open_banking_archiver \
    -e SMTP_HOST=my_smtp_server \
    -e SMTP_PORT=465 \
    -e SMTP_USERNAME=my_smtp_username \
    -e SMTP_PASSWORD=my_smtp_password \
    -e FROM_EMAIL='Open Banking Archiver <open-banking-archiver@mydomain.com>' \
    -e USER_EMAIL=my-email@mydomain.com \
    sebcoetzee/open-banking-archiver:latest
```

### Development Environment

A VS Code Dev Container setup is defined under the `.devcontainer` folder. This allows VS Code to create a development environment for the project with all the required dependencies already installed. Read more on [VS Code website](https://code.visualstudio.com/docs/devcontainers/containers).

### Dependency Management

This project uses [pip-tools](https://github.com/jazzband/pip-tools) to manage its python dependencies. To install dependencies:

```
python3 -m pip install -r requirements.txt
```

To add a dependency, add it to `requirements.in`, and run:

```
pip-compile
```

This will add the dependency to the `requirements.txt`. Now you may install all dependencies using:

```
python3 -m pip install -r requirements.txt
```

During development you will want to install the development depenvencies in addition to the application dependencies:

```
python3 -m pip install -r dev-requirements.txt
```
