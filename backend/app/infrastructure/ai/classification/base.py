"""Abstract base classifier contract for the email classification subsystem."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from infrastructure.ai.classification.exceptions import (
    ClassificationInputError,
    ClassifierNotReadyError,
)
from infrastructure.ai.classification.schemas import (
    ClassificationResult,
    EmailClassificationInput,
)

logger = logging.getLogger(__name__)


class BaseClassifier(ABC):
    """Defines the interface that every classifier implementation must satisfy.

    Concrete classifiers (embedding-based, zero-shot, LLM fallback) inherit
    from this class and implement :meth:`classify` and :meth:`is_ready`.

    Design contract
    ---------------
    * :meth:`classify` must be callable only when :meth:`is_ready` returns
      ``True``; otherwise it must raise :class:`~infrastructure.ai.classification.exceptions.ClassifierNotReadyError`.
    * :meth:`classify` must always return a :class:`~infrastructure.ai.classification.schemas.ClassificationResult`
      whose ``method`` field matches :attr:`method_name`.
    * Implementations must never swallow exceptions silently; failures must
      propagate as subclasses of :class:`~infrastructure.ai.classification.exceptions.ClassificationError`.
    * Implementations must not log email content at any log level.
    """

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def method_name(self) -> str:
        """Return the canonical method identifier for this classifier.

        The returned value must be one of the ``CLASSIFICATION_METHOD_*``
        constants defined in :mod:`core.constants` so that it can be
        persisted in the audit log without further transformation.

        Returns:
            A non-empty string identifying this classifier in audit records.
        """

    @abstractmethod
    def is_ready(self) -> bool:
        """Report whether this classifier is initialised and ready to serve requests.

        Implementations should verify that any required models, tokenisers, or
        external connections are available before returning ``True``.

        Returns:
            ``True`` if :meth:`classify` can be called safely, ``False`` otherwise.
        """

    @abstractmethod
    def classify(self, input_data: EmailClassificationInput) -> ClassificationResult:
        """Classify a single email and return a structured result.

        Args:
            input_data: Validated input DTO carrying the email's text content
                and metadata required for classification.

        Returns:
            A :class:`~infrastructure.ai.classification.schemas.ClassificationResult`
            with a valid category, confidence score, and method identifier.

        Raises:
            ClassifierNotReadyError: When the classifier has not been
                initialised.
            ClassificationInputError: When ``input_data`` cannot produce any
                usable text for inference.
            ClassificationInferenceError: When the underlying model raises an
                unexpected error during inference.
            ClassificationTimeoutError: When inference exceeds the configured
                deadline (applies to remote classifiers).
            LowConfidenceError: When no category meets the minimum confidence
                threshold configured for this classifier.
        """

    # ------------------------------------------------------------------
    # Optional lifecycle hooks
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load models and resources required by this classifier.

        Subclasses that require heavyweight initialisation (e.g. loading a
        HuggingFace model from disk) should override this method.  The default
        implementation is a no-op.

        This method is called by the orchestration layer before the first
        :meth:`classify` call, and may be called again to force a reload.
        """
        logger.debug("load() called on %s (no-op default).", self.__class__.__name__)

    def unload(self) -> None:
        """Release models and resources held by this classifier.

        Subclasses that hold references to large in-memory models should
        override this method to free that memory.  The default implementation
        is a no-op.
        """
        logger.debug("unload() called on %s (no-op default).", self.__class__.__name__)

    # ------------------------------------------------------------------
    # Shared helpers available to all subclasses
    # ------------------------------------------------------------------

    def _assert_ready(self) -> None:
        """Raise :class:`~infrastructure.ai.classification.exceptions.ClassifierNotReadyError` if not ready.

        Convenience guard that concrete :meth:`classify` implementations can
        call at the top of their bodies to enforce the readiness contract
        without duplicating the check.

        Raises:
            ClassifierNotReadyError: When :meth:`is_ready` returns ``False``.
        """
        if not self.is_ready():
            raise ClassifierNotReadyError(self.__class__.__name__)

    def _assert_input_has_text(self, input_data: EmailClassificationInput) -> str:
        """Return classification text or raise if the input yields an empty string.

        Delegates text construction to
        :meth:`~infrastructure.ai.classification.schemas.EmailClassificationInput.build_classification_text`
        and raises a descriptive error when the result is empty.

        Args:
            input_data: The input DTO to validate and extract text from.

        Returns:
            A non-empty string ready for model input.

        Raises:
            ClassificationInputError: When the constructed text is empty.
        """
        text = input_data.build_classification_text()
        if not text:
            raise ClassificationInputError(
                f"No usable text could be extracted from email "
                f"'{input_data.gmail_message_id}' for classification."
            )
        return text

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """Return a debug representation of this classifier instance.

        Returns:
            A string showing the class name and readiness status.
        """
        return f"<{self.__class__.__name__} method={self.method_name!r} ready={self.is_ready()}>"
