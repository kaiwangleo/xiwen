import httpx

from app.conf.app_config import EmbeddingConfig, app_config


class LocalEmbeddingClient:
    def __init__(self, base_url: str, path: str = "/embed", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.path = path if path.startswith("/") else f"/{path}"
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self):
        await self._client.aclose()

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.post(
            f"{self.base_url}{self.path}",
            json={"inputs": texts},
        )
        response.raise_for_status()
        return response.json()

    async def aembed_query(self, text: str) -> list[float]:
        return (await self.aembed_documents([text]))[0]

    async def health(self) -> None:
        """Raise when the embedding service health endpoint is unavailable."""
        response = await self._client.get(f"{self.base_url}/health")
        response.raise_for_status()


class EmbeddingClientManager:
    def __init__(self, config: EmbeddingConfig):
        self.client: LocalEmbeddingClient | None = None
        self.config = config

    def _get_url(self):
        return f"http://{self.config.host}:{self.config.port}"

    def init(self):
        self.client = LocalEmbeddingClient(
            self._get_url(),
            path=self.config.path,
            timeout=self.config.timeout,
        )

    async def reload(self):
        old = self.client
        self.init()
        if old:
            await old.aclose()


embedding_client_manager = EmbeddingClientManager(app_config.embedding)
