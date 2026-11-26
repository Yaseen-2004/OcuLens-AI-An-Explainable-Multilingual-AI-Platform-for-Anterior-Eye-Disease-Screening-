# OcuLens-AI clinic portal - on-premise / private-cloud image (CPU only)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    OCULENS_DATA_DIR=/data OCULENS_DEMO_MODE=0

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# CPU-only PyTorch keeps the image small (no CUDA libraries)
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision \
    && pip install -r requirements.txt

COPY . .
RUN useradd --create-home oculens && mkdir -p /data && chown -R oculens /data /app
USER oculens

EXPOSE 8501
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD curl -fs http://localhost:8501/_stcore/health || exit 1
CMD ["python", "-m", "streamlit", "run", "portal/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
