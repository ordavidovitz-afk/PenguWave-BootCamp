import requests
from openai import AzureOpenAI
from typing import Optional
import os
import logging

log_level = os.getenv("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)

if log_level != "DEBUG":
    for noisy in ("azure.core.pipeline.policies.http_logging_policy",
                  "azure.identity", "httpx", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


class AzureAIFoundryClient:


    def __init__(self):
        self.openai_client = self._setup_openai_client()

    # ---------- Init ----------
    def _setup_openai_client(self) -> AzureOpenAI:
        api_key = os.getenv("AZURE_OPENAI_MONITORING_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = "2024-12-01-preview"

        if not api_key or not azure_endpoint:
            logger.error("Missing Azure OpenAI credentials")
            raise EnvironmentError("Missing AZURE_OPENAI_MONITORING_KEY or AZURE_OPENAI_ENDPOINT")

        logger.debug("Initializing AzureOpenAI client")
        
        # Fix gevent/trio conflict (only needed when using gevent for WebSockets)
        # gevent monkey-patches async primitives which breaks trio
        # This is safe for all environments - it only blocks trio if not already loaded
        import sys
        if 'trio' not in sys.modules:
            sys.modules['trio'] = None  # Block trio import
            sys.modules['trio._core'] = None
            sys.modules['trio._core._run'] = None
        
        return AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint,
        )

    # ---------- Chat completion ----------
    def generate_completion(
        self,
        deployment_name: str,
        messages: Optional[list[dict]] = None,
        prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> Optional[str]:
        if messages is None:
            if prompt is None:
                raise ValueError("Either messages or prompt must be provided")
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ]
        elif not any(m["role"] == "system" for m in messages):
            messages.insert(0, {"role": "system", "content": "You are a helpful assistant."})

        params = {
            "model": deployment_name,
            "messages": messages,
            "temperature": temperature,
            **({"max_tokens": max_tokens} if max_tokens is not None else {}),
        }

        try:
            response = self.openai_client.chat.completions.create(**params)
            return response.choices[0].message.content if response.choices else None
        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            return None
    
    # ---------- Embeddings ----------
    def generate_embeddings(
        self,
        texts: list[str],
        model: str = "text-embedding-3-large"
    ) -> list[list[float]]:
        """
        Generate embeddings for a list of texts using Azure OpenAI.
        
        Args:
            texts: List of text strings to embed
            model: Embedding model to use (default: text-embedding-3-large, 3072 dimensions)
            
        Returns:
            List of embedding vectors (each is a list of floats, typically 3072 for text-embedding-3-large)
            
        Note:
            - text-embedding-3-large produces 3072-dimensional embeddings
            - text-embedding-3-small produces 1536-dimensional embeddings
            - Can process up to 2048 texts in a single API call
        """
        if not texts:
            logger.warning("No texts provided for embedding generation")
            return []
        
        try:
            logger.debug(f"Generating embeddings for {len(texts)} texts using model '{model}'")
            
            response = self.openai_client.embeddings.create(
                model=model,
                input=texts
            )
            
            embeddings = [data.embedding for data in response.data]
            
            logger.info(
                f"Successfully generated {len(embeddings)} embeddings "
                f"({len(embeddings[0])} dimensions each)"
            )
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings with model '{model}': {e}")
            return []