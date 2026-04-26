FROM python:3.11-slim

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false && poetry install --without dev

COPY . .

CMD uvicorn main:app --host 0.0.0.0 --port $PORT
