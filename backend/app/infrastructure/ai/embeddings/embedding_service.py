"""Sentence-transformers embedding service with thread-safe singleton model loading."""

from __future__ import annotations

import threading
from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

from core.config import get_settings


class EmbeddingService:
    """Generate semantic embeddings using a lazily loaded singleton model.

    The underlying SentenceTransformer model is loaded once per process and
    shared across all EmbeddingService instances. Model initialisation is
    protected by a lock to ensure thread-safe first access.
    """

    _model: SentenceTransformer | None = None
    _model_lock = threading.Lock()
    _instance: EmbeddingService | None = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> "EmbeddingService":
        """Return the process-wide EmbeddingService singleton."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def model(self) -> SentenceTransformer:
        """Return the shared embedding model, loading it on first use."""
        if self.__class__._model is None:
            with self.__class__._model_lock:
                if self.__class__._model is None:
                    settings = get_settings()
                    self.__class__._model = SentenceTransformer(
                        model_name_or_path=settings.embedding_model_name,
                        cache_folder=settings.huggingface_cache_dir,
                    )
        return self.__class__._model

    def is_ready(self) -> bool:
        """Return True when the embedding model has already been loaded."""
        return self.__class__._model is not None

    def embed_text(self, text: str) -> NDArray[np.float32]:
        """Generate a single embedding vector for the provided text.

        Args:
            text: Input text to embed.

        Returns:
            A one-dimensional numpy array containing the embedding vector.

        Raises:
            ValueError: If text is empty after trimming whitespace.
        """
        normalized_text = text.strip()
        if not normalized_text:
            raise ValueError("Text must not be empty.")

        embedding = self.model.encode(
            normalized_text,
            convert_to_numpy=True,
            normalize_embeddings=False,
        )
        return np.asarray(embedding, dtype=np.float32)

    def embed_texts(self, texts: Sequence[str]) -> NDArray[np.float32]:
        """Generate embeddings for multiple texts in a single batch.

        Args:
            texts: A sequence of texts to embed.

        Returns:
            A two-dimensional numpy array with one embedding per input text.

        Raises:
            ValueError: If no texts are provided or any text is empty after trimming.
        """
        normalized_texts = [text.strip() for text in texts]
        if not normalized_texts:
            raise ValueError("At least one text is required for batch embedding.")
        if any(not text for text in normalized_texts):
            raise ValueError("Batch embedding input contains an empty text value.")

        embeddings = self.model.encode(
            normalized_texts,
            convert_to_numpy=True,
            normalize_embeddings=False,
        )
        return np.asarray(embeddings, dtype=np.float32)

    def unload(self) -> None:
        """Release the loaded model from memory."""
        with self.__class__._model_lock:
            self.__class__._model = None

    @classmethod
    def reset_singleton(cls) -> None:
        """Reset the service and model singletons.

        This helper is intended for test isolation and controlled reloads.
        """
        with cls._instance_lock:
            cls._instance = None
        with cls._model_lock:
            cls._model = None
