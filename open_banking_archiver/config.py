import os
from dataclasses import dataclass
from functools import cache


@dataclass(frozen=True)
class Config:
    nordigen_secret_id: str
    nordigen_secret_key: str
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    from_email: str
    user_email: str


def read_environment_variable(variable_name: str, readable_name: str) -> str:
    variable_name = variable_name.upper()
    result: str | None
    if variable_file_path := os.environ.get(f"{variable_name}_FILE"):
        with open(variable_file_path, "r") as variable_file:
            result = variable_file.read()
    else:
        result = os.environ.get(variable_name)

    assert result, (
        f"A {readable_name} should be provided, either in the form of the `{variable_name}` "
        "environment variable or in a file whose path is passed via the "
        f"`{variable_name}_FILE` environment variable"
    )

    return result


@cache
def resolve_config() -> Config:
    return Config(
        nordigen_secret_id=read_environment_variable("nordigen_secret_id", "Nordigen secret ID"),
        nordigen_secret_key=read_environment_variable("nordigen_secret_key", "Nordigen secret key"),
        db_host=read_environment_variable("db_host", "DB host"),
        db_port=int(read_environment_variable("db_port", "DB port")),
        db_user=read_environment_variable("db_user", "DB user"),
        db_password=read_environment_variable("db_password", "DB password"),
        db_name=read_environment_variable("db_name", "DB name"),
        smtp_host=read_environment_variable("smtp_host", "SMTP host"),
        smtp_port=int(read_environment_variable("smtp_port", "SMTP port")),
        smtp_username=read_environment_variable("smtp_username", "SMTP username"),
        smtp_password=read_environment_variable("smtp_password", "SMTP password"),
        from_email=read_environment_variable("from_email", "From email"),
        user_email=read_environment_variable("user_email", "User email"),
    )
