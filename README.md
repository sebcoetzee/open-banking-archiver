# Open Banking Archiver

Python-based application that requests Open Banking data from the Nordigen API and inserts it into a PostgreSQL database.

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
