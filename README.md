# Open Banking Archiver

Python-based application that requests Open Banking data from the Nordigen API and inserts it into a PostgreSQL database.

### Installation

The dev container is defined for VS Code. Read more on [VS Code website](https://code.visualstudio.com/docs/devcontainers/containers).

This project uses [pip-tools](https://github.com/jazzband/pip-tools) to manage dependencies. To install dependencies:

```
python3 -m pip install -r requirements.txt
```

To add a dependency, add it to `requirements.in`, and install it:

```
python3 -m pip install <dependency>
```

Add it to `requirements.txt`:

```
pip-compile
```
