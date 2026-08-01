"""OpenAI-compatible LLM provider implementation."""

import logging
from typing import Any

import httpx
import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible API provider (supports OpenAI, DeepSeek, vLLM, Ollama, etc.)."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        verify_ssl: bool = True,
        timeout: float = 30.0,
    ):
        """
        Initialize OpenAI-compatible provider.

        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
            model: Model name to use
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
        """
        super().__init__(base_url, api_key, model, verify_ssl)
        self.timeout = timeout

        # Create HTTP client with SSL verification toggle
        http_client = httpx.AsyncClient(
            verify=verify_ssl, timeout=httpx.Timeout(timeout)
        )

        # Create OpenAI client
        self.client = AsyncOpenAI(
            api_key=api_key, base_url=base_url, http_client=http_client
        )

        # Patch with Instructor for structured outputs
        # Use JSON mode for DeepSeek to avoid tool_choice conflicts with reasoning mode
        instructor_mode = (
            instructor.Mode.JSON
            if "deepseek" in model.lower()
            else instructor.Mode.TOOLS
        )
        self.instructor_client = instructor.from_openai(
            self.client, mode=instructor_mode
        )

        logger.info(
            f"Initialized OpenAI-compatible provider: model={model}, "
            f"base_url={base_url}, verify_ssl={verify_ssl}"
        )

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "openai-compatible"

    async def generate_completion(
        self,
        prompt: str,
        response_model: type[BaseModel],
        max_retries: int = 3,
        **kwargs: Any,
    ) -> BaseModel:
        """
        Generate a structured completion using Instructor.

        Args:
            prompt: The prompt to send to the LLM
            response_model: Pydantic model for structured output
            max_retries: Maximum number of retries on failure
            **kwargs: Additional parameters (temperature, etc.)

        Returns:
            Instance of response_model with LLM-generated data

        Raises:
            Exception: If LLM call fails after all retries
        """
        try:
            # Log request details
            logger.info(
                f"🤖 LLM Request - Model: {self.model}, Response Type: {response_model.__name__}, Max Retries: {max_retries}"
            )
            logger.debug(f"📝 LLM Prompt:\n{'-' * 80}\n{prompt}\n{'-' * 80}")
            logger.debug(f"⚙️  LLM Parameters: {kwargs}")

            # Use Instructor to get structured output
            # Mode is set at client initialization (JSON for DeepSeek, TOOLS for others)
            response = await self.instructor_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_model=response_model,
                max_retries=max_retries,
                **kwargs,
            )

            # Log response details
            logger.info(f"✅ LLM Response - Type: {type(response).__name__}")
            logger.debug(
                f"📦 LLM Response Data:\n{'-' * 80}\n{response.model_dump_json(indent=2)}\n{'-' * 80}"
            )

            return response

        except Exception as e:
            logger.error(f"❌ LLM completion failed: {e}")
            raise

    async def generate_completion_stream(self, prompt: str, **kwargs: Any):
        """
        Generate a streaming completion (token-by-token).

        Args:
            prompt: The prompt to send to the LLM
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Yields:
            Individual tokens/chunks from the LLM as they arrive

        Example:
            ```python
            async for token in provider.generate_completion_stream("Hello"):
                print(token, end="", flush=True)
            ```
        """
        try:
            # Log request details
            logger.info(f"🌊 LLM Streaming Request - Model: {self.model}")
            logger.debug(f"📝 LLM Streaming Prompt:\n{'-' * 80}\n{prompt}\n{'-' * 80}")
            logger.debug(f"⚙️  LLM Streaming Parameters: {kwargs}")

            # Create streaming completion
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                **kwargs,
            )

            # Track tokens for logging
            token_count = 0
            full_response = []

            # Yield tokens as they arrive
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        token_count += 1
                        full_response.append(delta.content)
                        yield delta.content

            # Log completion summary
            complete_text = "".join(full_response)
            logger.info(
                f"✅ LLM Streaming Complete - Tokens: {token_count}, Length: {len(complete_text)} chars"
            )
            logger.debug(
                f"📦 LLM Streaming Response:\n{'-' * 80}\n{complete_text}\n{'-' * 80}"
            )

        except Exception as e:
            logger.error(f"❌ LLM streaming completion failed: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        if hasattr(self.client, "_client") and hasattr(self.client._client, "aclose"):
            await self.client._client.aclose()
