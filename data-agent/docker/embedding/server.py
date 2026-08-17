import os

from fastapi import FastAPI, Request
from sentence_transformers import SentenceTransformer
import uvicorn

MODEL_ID = os.getenv("MODEL_ID", "BAAI/bge-large-zh-v1.5")
PORT = int(os.getenv("PORT", "80"))

model = SentenceTransformer(MODEL_ID)
app = FastAPI()


def encode(texts: list[str]) -> list[list[float]]:
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()


def extract_texts(payload) -> list[str]:
    if isinstance(payload, list):
        return [str(x) for x in payload]
    if isinstance(payload, str):
        return [payload]
    if isinstance(payload, dict):
        value = payload.get("inputs", payload.get("input", payload.get("text")))
        if isinstance(value, list):
            return [str(x) for x in value]
        if value is not None:
            return [str(value)]
    raise ValueError("unsupported embedding payload")


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_ID, "dim": model.get_sentence_embedding_dimension()}


@app.post("/")
@app.post("/embed")
@app.post("/pipeline/feature-extraction")
async def embed(request: Request):
    payload = await request.json()
    return encode(extract_texts(payload))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
