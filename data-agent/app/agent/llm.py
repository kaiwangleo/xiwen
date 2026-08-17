from langchain.chat_models import init_chat_model
from langchain_core.runnables import Runnable

from app.conf.app_config import app_config


def _build_llm():
    return init_chat_model(
        model=app_config.llm.model_name,
        model_provider="openai",
        api_key=app_config.llm.api_key,
        base_url=app_config.llm.base_url,
        temperature=app_config.llm.temperature,
        timeout=app_config.llm.timeout,
    )


class ReloadableLLM(Runnable):
    """Nodes import this object once; swap the inner model without restart."""

    def __init__(self):
        self._inner = _build_llm()

    def reload(self) -> None:
        self._inner = _build_llm()

    def invoke(self, input, config=None, **kwargs):
        return self._inner.invoke(input, config=config, **kwargs)

    async def ainvoke(self, input, config=None, **kwargs):
        return await self._inner.ainvoke(input, config=config, **kwargs)

    def stream(self, input, config=None, **kwargs):
        return self._inner.stream(input, config=config, **kwargs)

    async def astream(self, input, config=None, **kwargs):
        async for chunk in self._inner.astream(input, config=config, **kwargs):
            yield chunk

    def batch(self, inputs, config=None, **kwargs):
        return self._inner.batch(inputs, config=config, **kwargs)

    async def abatch(self, inputs, config=None, **kwargs):
        return await self._inner.abatch(inputs, config=config, **kwargs)

    def __getattr__(self, name):
        return getattr(self._inner, name)


llm = ReloadableLLM()


if __name__ == "__main__":
    for chunk in llm.stream("What is the meaning of life?"):
        print(chunk.text)
