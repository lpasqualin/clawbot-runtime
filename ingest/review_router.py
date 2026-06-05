import os
from dataclasses import dataclass
from typing import Optional

VAULT_ROOT = "/home/leo-paz/obsidian-vault"
PENDING_DIR = "/home/leo-paz/obsidian-vault/05 - Ingest/Pending"
AUTO_FILE_CONFIDENCE_THRESHOLD = 0.80

# Classifier destination prefixes that don't match the actual vault folder names.
# Keyed by the prefix the classifier emits; value is the real vault top-level folder.
DESTINATION_CORRECTIONS = {
    "20 - BBS":      "10 - BBS",
    "30 - ClawBot":  "20 - ClawBot",
    "60 - Projects": "40 - Ventures",
}

# Content types that always require human review regardless of confidence.
SENSITIVE_CONTENT_TYPES = {"resume", "personal"}

# Tag values that flag a document as sensitive.
SENSITIVE_TAGS = {"payroll", "sensitive", "private", "personal", "pii"}

# Filename substrings that flag a document as sensitive.
SENSITIVE_FILENAME_PATTERNS = ("paystatement", "paystub", "w-2", "w2", "1099", "ssn")


@dataclass
class RouteDecision:
    action: str        # "auto_file" or "pending_review"
    destination: str   # absolute path to target directory
    reason: str
    sensitive: bool
    confidence: float


class ReviewRouter:

    def __init__(
        self,
        vault_root: str = VAULT_ROOT,
        pending_dir: str = PENDING_DIR,
        confidence_threshold: float = AUTO_FILE_CONFIDENCE_THRESHOLD,
    ):
        self.vault_root = vault_root
        self.pending_dir = pending_dir
        self.confidence_threshold = confidence_threshold

    def is_sensitive(self, doc_meta: dict) -> bool:
        content_type = (doc_meta.get("content_type") or "").lower().strip()
        if content_type in SENSITIVE_CONTENT_TYPES:
            return True

        tags_raw = doc_meta.get("tags") or ""
        if isinstance(tags_raw, str):
            tags = {t.strip().lower() for t in tags_raw.split(",") if t.strip()}
        else:
            tags = set()
        if tags & SENSITIVE_TAGS:
            return True

        filename = (doc_meta.get("source_filename") or "").lower()
        if any(p in filename for p in SENSITIVE_FILENAME_PATTERNS):
            return True

        return False

    def resolve_destination(self, suggested_destination: Optional[str]) -> Optional[str]:
        if not suggested_destination:
            return None

        # Strip trailing slash; split into top-level folder and optional remainder.
        dest = suggested_destination.rstrip("/")
        if "/" in dest:
            top, remainder = dest.split("/", 1)
        else:
            top, remainder = dest, ""

        top = DESTINATION_CORRECTIONS.get(top, top)
        top_path = os.path.join(self.vault_root, top)
        if not os.path.isdir(top_path):
            return None

        if remainder:
            full_path = os.path.join(top_path, remainder)
            os.makedirs(full_path, exist_ok=True)
        else:
            full_path = top_path

        return full_path

    def route(self, doc_meta: dict) -> RouteDecision:
        confidence = float(doc_meta.get("confidence") or 0.0)
        sensitive = self.is_sensitive(doc_meta)

        if sensitive:
            return RouteDecision(
                action="pending_review",
                destination=self.pending_dir,
                reason="sensitive document — always pending review",
                sensitive=True,
                confidence=confidence,
            )

        if confidence < self.confidence_threshold:
            return RouteDecision(
                action="pending_review",
                destination=self.pending_dir,
                reason=f"confidence {confidence:.2f} below threshold {self.confidence_threshold:.2f}",
                sensitive=False,
                confidence=confidence,
            )

        dest = self.resolve_destination(doc_meta.get("suggested_destination"))
        if dest is None:
            return RouteDecision(
                action="pending_review",
                destination=self.pending_dir,
                reason=f"destination '{doc_meta.get('suggested_destination')}' not resolvable to vault folder",
                sensitive=False,
                confidence=confidence,
            )

        return RouteDecision(
            action="auto_file",
            destination=dest,
            reason=f"confidence {confidence:.2f} >= {self.confidence_threshold:.2f}, destination resolved",
            sensitive=False,
            confidence=confidence,
        )
