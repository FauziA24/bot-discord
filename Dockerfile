FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libffi8 libnacl2 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 botuser

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY index.py ./
COPY src ./src

USER botuser

CMD ["python", "index.py"]
