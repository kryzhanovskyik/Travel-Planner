FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry==2.3.2 && \
    poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./

RUN poetry install --only main --no-root

COPY src/ ./src/

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
