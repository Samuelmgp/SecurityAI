FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-cache the ONNX embedding model (~50 MB) so container startup is instant
RUN python -c "from fastembed import TextEmbedding; list(TextEmbedding('BAAI/bge-small-en-v1.5').embed(['warmup']))"

COPY . .

ENV PYTHONUNBUFFERED=1 \
    BOOKS_DIR=/app/book_data \
    CHROMA_DIR=/app/data/chroma

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
