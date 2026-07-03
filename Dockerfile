# ── GraphMind backend — Hugging Face Spaces (Docker SDK) ───────────────
# Build context = repo root.  The Space README must declare `app_port: 7860`.
# CPU-only torch keeps the image small (Spaces free tier has no GPU).
FROM python:3.12-slim

# HF Spaces run containers as a non-root user with UID 1000.
RUN useradd -m -u 1000 user
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860 \
    # writable caches for the embedding model (baked below, re-used at runtime)
    HF_HOME=/home/user/.cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/home/user/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/home/user/.cache/sentence-transformers

WORKDIR /app

# 1) CPU-only PyTorch. NOTE: backend/requirements.txt pins torch==2.2.0, which is
#    too old for the current sentence-transformers (model load fails with a torch
#    NameError). We install a recent CPU build here and drop that pin below.
RUN pip install --user --no-cache-dir \
        torch --index-url https://download.pytorch.org/whl/cpu

# 2) Backend dependencies (minus the torch pin — already satisfied above by the
#    recent CPU build; keeps the image small and avoids the incompatible 2.2.0).
COPY --chown=user backend/requirements.txt ./backend/requirements.txt
RUN grep -ivE '^[[:space:]]*torch[[:space:]]*==' backend/requirements.txt > /tmp/requirements.txt \
 && pip install --user --no-cache-dir -r /tmp/requirements.txt

# 3) Pre-download the embedding model into the image so the first request is
#    fast and boot does not depend on the HF Hub being reachable.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# The model is now baked in — run fully offline so startup makes no network
# calls to the HF Hub (faster boot, no dependency on Hub reachability).
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

# 4) Application code (this is the layer that changes most often).
COPY --chown=user backend ./backend

EXPOSE 7860

# Bind to $PORT (HF sets 7860). Single worker: the CQRS engine holds per-user
# graphs in memory, so do NOT scale to multiple workers/replicas.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
