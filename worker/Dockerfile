FROM python:3.11-slim

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-vie \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml chainlit_app.py /app/
COPY app /app/app
COPY worker /app/worker
RUN pip install --no-cache-dir .

CMD ["python", "-m", "worker.main"]
