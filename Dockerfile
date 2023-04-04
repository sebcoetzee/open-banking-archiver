FROM python:3.11.2-slim-bullseye

RUN mkdir -p /app

WORKDIR /app

COPY open_banking_archiver /app/open_banking_archiver/
COPY requirements.txt /app/

RUN python3 -m pip install -r requirements.txt

CMD ["python3", "-m", "open_banking_archiver", "--log-format=formatted", "--log-level=INFO", "sync", "transactions"]