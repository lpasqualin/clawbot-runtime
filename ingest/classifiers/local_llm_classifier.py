from classifiers.rules_classifier import ClassificationResult
from summarizers.local_llm_summarizer import LocalLLMSummarizer


class LLMClassifier:

    def __init__(self, model: str = None):
        self.model = model

    def classify(self, text: str, filename: str) -> ClassificationResult:
        try:
            summarizer = LocalLLMSummarizer(model=self.model)
            result = summarizer.summarize(text, filename, "unknown")

            if not result.success:
                return ClassificationResult(
                    project="",
                    destination="",
                    content_type="unknown",
                    tags=[],
                    confidence=0.0,
                    method="llm_failed",
                )

            return ClassificationResult(
                project=result.suggested_project,
                destination=result.suggested_destination,
                content_type="unknown",
                tags=list(result.tags),
                confidence=result.confidence,
                method="llm",
            )
        except Exception:
            return ClassificationResult(
                project="",
                destination="",
                content_type="unknown",
                tags=[],
                confidence=0.0,
                method="llm_failed",
            )
