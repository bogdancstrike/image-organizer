# syntax=docker/dockerfile:1.7
# ---------- 1. build the React UI ----------
FROM node:22-alpine AS ui
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- 2. runtime: FastAPI + CLIP (ONNX) + ffmpeg ----------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LIBRARY_ROOT=/library \
    DATA_DIR=/data \
    MODEL_DIR=/models \
    STATIC_DIR=/app/static \
    HF_HUB_DISABLE_TELEMETRY=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg gosu libgl1 libegl1 libgles2 libglib2.0-0 libportaudio2 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# Bundle the CLIP models and the MediaPipe face model so the container works offline (REQ-ANL-2)
RUN python -c "from fastembed import ImageEmbedding, TextEmbedding; \
ImageEmbedding('Qdrant/clip-ViT-B-32-vision', cache_dir='/models'); \
TextEmbedding('Qdrant/clip-ViT-B-32-text', cache_dir='/models')" \
 && python -c "import urllib.request; urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task', '/models/face_landmarker.task')" \
 && chmod -R a+rX /models
ENV HF_HUB_OFFLINE=1 \
    FACE_MODEL=/models/face_landmarker.task \
    MPLCONFIGDIR=/tmp/matplotlib \
    GLOG_minloglevel=2 \
    MALLOC_ARENA_MAX=2

COPY backend/ ./
COPY --from=ui /ui/dist /app/static
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && mkdir -p /data /library

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "--factory", "app.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
