FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app/src PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY config ./config
COPY eval ./eval
COPY data/sample ./data/sample

EXPOSE 8000
CMD ["uvicorn", "marketmind.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
