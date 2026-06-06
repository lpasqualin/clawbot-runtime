from classifiers.rules_classifier import ClassificationResult, ALLOWED_ROOTS, _subfolder_exists
from summarizers.local_llm_summarizer import LocalLLMSummarizer


def _count_signals(evidence: list, document_type: str) -> int:
    """
    Count independent signals from LLM evidence list.
    Categories: doctype, entity, content — max 1 per category.
    """
    has_doctype = document_type not in ("other", "")
    has_entity = any("entity:" in e.lower() for e in evidence)
    has_content = any(
        any(kw in e.lower() for kw in ("keyword:", "content:", "pattern:", "structure:"))
        for e in evidence
    )
    return int(has_doctype) + int(has_entity) + int(has_content)


class LLMClassifier:

    def __init__(self, model: str = None):
        self.model = model

    def classify(self, text: str, filename: str) -> ClassificationResult:
        try:
            summarizer = LocalLLMSummarizer(model=self.model)
            result = summarizer.summarize(text, filename, "unknown")

            if not result.success:
                return ClassificationResult(
                    document_type="other", root="", relative_path="", suggested_subfolder="",
                    path_exists=False, confidence=0.0, reason="LLM summarizer failed",
                    evidence=[], signal_count=0, needs_review=True,
                    tags=[], method="llm_failed",
                )

            root = result.root
            if root not in ALLOWED_ROOTS:
                return ClassificationResult(
                    document_type=result.document_type, root="", relative_path="",
                    suggested_subfolder="", path_exists=False,
                    confidence=0.0, reason=f"LLM returned invalid root: {root!r}",
                    evidence=result.evidence, signal_count=0, needs_review=True,
                    tags=list(result.tags), method="llm_invalid_root",
                )

            signal_count = _count_signals(result.evidence, result.document_type)

            return ClassificationResult(
                document_type=result.document_type,
                root=root,
                relative_path=root,
                suggested_subfolder=result.suggested_subfolder,
                path_exists=result.path_exists,
                confidence=result.confidence,
                reason=result.reason,
                evidence=list(result.evidence),
                signal_count=signal_count,
                needs_review=result.needs_review,
                tags=list(result.tags),
                method="llm",
                summary=result.summary,
            )
        except Exception as exc:
            return ClassificationResult(
                document_type="other", root="", relative_path="", suggested_subfolder="",
                path_exists=False, confidence=0.0, reason=f"LLM classifier exception: {exc}",
                evidence=[], signal_count=0, needs_review=True,
                tags=[], method="llm_failed",
            )
