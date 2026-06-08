"""Exception hierarchy for the email classification subsystem."""


class ClassificationError(Exception):
    """Base exception for all classification failures.

    All classifier implementations must raise subclasses of this exception
    so callers can handle classification-specific errors uniformly.
    """

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        """Initialise the exception with an optional chained cause.

        Args:
            message: Human-readable description of the failure.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(message)
        self.__cause__ = cause


class ClassifierNotReadyError(ClassificationError):
    """Raised when a classifier is invoked before it has been initialised.

    Typically surfaced when a model has not been loaded or a required
    external resource is unavailable at the time of the call.
    """

    def __init__(self, classifier_name: str) -> None:
        """Initialise with the name of the unready classifier.

        Args:
            classifier_name: Identifier of the classifier that is not ready.
        """
        super().__init__(
            f"Classifier '{classifier_name}' is not ready. "
            "Ensure the model has been loaded before calling classify()."
        )
        self.classifier_name = classifier_name


class ClassificationInputError(ClassificationError):
    """Raised when the input provided to a classifier is invalid.

    Covers cases such as empty text, text that exceeds the model's maximum
    token limit, or a ``None`` value where a string is required.
    """

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        """Initialise with a description of the invalid input.

        Args:
            message: Description of why the input is invalid.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(message, cause=cause)


class ClassificationInferenceError(ClassificationError):
    """Raised when model inference fails during classification.

    Covers runtime failures such as CUDA out-of-memory errors, tokenisation
    failures, or unexpected model output shapes.
    """

    def __init__(
        self,
        classifier_name: str,
        message: str,
        *,
        cause: BaseException | None = None,
    ) -> None:
        """Initialise with the classifier name and a description of the failure.

        Args:
            classifier_name: Identifier of the classifier that failed.
            message: Description of the inference failure.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(
            f"Inference error in classifier '{classifier_name}': {message}",
            cause=cause,
        )
        self.classifier_name = classifier_name


class ClassificationTimeoutError(ClassificationError):
    """Raised when a classification call exceeds the configured timeout.

    Applies to classifiers that perform remote calls (e.g. LLM fallback) or
    have configurable inference deadlines.
    """

    def __init__(
        self,
        classifier_name: str,
        timeout_seconds: float,
    ) -> None:
        """Initialise with the classifier name and the elapsed timeout.

        Args:
            classifier_name: Identifier of the classifier that timed out.
            timeout_seconds: The timeout value that was exceeded, in seconds.
        """
        super().__init__(
            f"Classifier '{classifier_name}' timed out after {timeout_seconds}s."
        )
        self.classifier_name = classifier_name
        self.timeout_seconds = timeout_seconds


class LowConfidenceError(ClassificationError):
    """Raised when no category meets the minimum confidence threshold.

    Signals to the orchestration layer that the current classifier could not
    produce a reliable result and a fallback strategy should be attempted.
    """

    def __init__(
        self,
        classifier_name: str,
        best_category: str,
        best_score: float,
        threshold: float,
    ) -> None:
        """Initialise with scoring context that explains the failure.

        Args:
            classifier_name: Identifier of the classifier that returned low confidence.
            best_category: The highest-scoring category that was found.
            best_score: The confidence score associated with ``best_category``.
            threshold: The minimum confidence threshold that was not met.
        """
        super().__init__(
            f"Classifier '{classifier_name}' best match '{best_category}' scored "
            f"{best_score:.4f}, which is below the required threshold of {threshold:.4f}."
        )
        self.classifier_name = classifier_name
        self.best_category = best_category
        self.best_score = best_score
        self.threshold = threshold
