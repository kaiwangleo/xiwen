FROM docker.m.daocloud.io/library/python:3.12-slim

WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 \
    HF_ENDPOINT=https://hf-mirror.com \
    MODEL_ID=BAAI/bge-large-zh-v1.5 \
    PORT=80

RUN pip install --upgrade pip \
    && pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install fastapi uvicorn sentence-transformers

COPY server.py /app/server.py

EXPOSE 80
CMD ["python", "server.py"]
