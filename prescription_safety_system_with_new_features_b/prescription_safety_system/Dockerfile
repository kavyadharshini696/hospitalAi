FROM python:3.11-slim

# tesseract-ocr is a system binary that pytesseract calls out to — pip cannot
# install it, so it has to come from the OS package manager here.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render sets $PORT at runtime; gunicorn binds to it. 2 workers is a
# reasonable default for the free tier's limited CPU/RAM.
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120 app:app