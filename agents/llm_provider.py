import os
import re
import json
import httpx
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type

T = TypeVar("T", bound=BaseModel)

class YandexGPTProvider:
    """Адаптер для вызова YandexGPT с гарантией структурированного вывода"""
    
    def __init__(self):
        self.iam_token = os.getenv("YANDEX_IAM_TOKEN")
        self.folder_id = os.getenv("YANDEX_FOLDER_ID")
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    @retry(
        wait=wait_random_exponential(multiplier=1, min=2, max=15),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        reraise=True,
    )
    async def _call_api(self, payload: dict) -> dict:
        if not self._client:
            raise RuntimeError("Provider must be used as async context manager")
            
        headers = {
            "Authorization": f"Bearer {self.iam_token}",
            "x-folder-id": self.folder_id,
            "Content-Type": "application/json",
        }
        response = await self._client.post(self.base_url, json=payload, headers=headers)

        if response.status_code in (429, 500, 502, 503, 504):
            raise httpx.HTTPStatusError(
                f"Retryable error: {response.status_code}", 
                request=response.request, 
                response=response
            )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _clean_json_string(raw_text: str) -> str:
        """Удаляет markdown-обертки ```json ... ```, которые часто генерирует LLM"""
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else raw_text.strip()

    async def agenerate_structured(self, prompt: str, response_model: Type[T]) -> T:
        """Генерация структурированного ответа с гарантией валидации"""
        payload = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt/latest",
            "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": 1000},
            "messages": [
                {
                    "role": "system", 
                    "text": "Ты — AI-ассистент для ведения диалогов с должниками. Отвечай строго в формате JSON, без markdown-оберток и лишнего текста."
                },
                {"role": "user", "text": prompt},
            ],
        }

        data = await self._call_api(payload)

        try:
            raw_text = data["result"]["alternatives"][0]["message"]["text"]
        except KeyError as e:
            raise ValueError(f"Unexpected YandexGPT response structure: {data}") from e

        try:
            cleaned_text = self._clean_json_string(raw_text)
            parsed = json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON. Raw: {raw_text[:200]}...") from e

        try:
            return response_model.model_validate(parsed)
        except ValidationError as e:
            raise ValueError(f"Response validation failed against schema: {e}") from e