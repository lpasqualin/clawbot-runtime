import os
from dataclasses import dataclass
from typing import Optional

VAULT_ROOT = "/home/leo-paz/obsidian-vault"
PENDING_DIR = "/home/leo-paz/obsidian-vault/05 - Ingest/Pending"

# Auto-file: all 4 conditions required
AUTO_FILE_CONFIDENCE = 0.90
# Pending strong suggestion: confident but missing subfolder or single signal
PENDING_STRONG_CONFIDENCE = 0.80

# Content types that always require human review.
SENSITIVE_CONTENT_TYPES = {"resume", "personal"}

# Tag values that flag a document as sensitive.
SENSITIVE_TAGS = {"payroll", "sensitive", "private", "personal", "pii"}

# Filename substrings that flag a document as sensitive.
SENSITIVE_FILENAME_PATTERNS = ("paystatement", "paystub", "w-2", "w2", "1099", "ssn")


@dataclass
class RouteDecision:
    action: str        # "auto_file" | "pending_review" | "pending_strong"
    destination: str   # absolute path to target directory
    reason: str
    sensitive: bool
    confidence: float


class ReviewRouter:

    def __init__(
        self,
        vault_root: str = VAULT_ROOT,
        pending_dir: str = PENDING_DIR,
    ):
        self.vault_root = vault_root
        self.pending_dir = pending_dir

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

    def resolve_destination(self, suggested_destination: Optional[str], subfolder: Optional[str] = None) -> Optional[str]:
        """Resolve vault destination to an absolute path. Root must exist; subfolder is created if needed."""
        if not suggested_destination:
            return None
        root = suggested_destination.strip().rstrip("/")
        full_path = os.path.join(self.vault_root, root)
        if not full_path.startswith(self.vault_root):
            return None
        if not os.path.isdir(full_path):
            return None
        if subfolder:
            full_path = os.path.join(full_path, subfolder.strip().strip("/"))
            os.makedirs(full_path, exist_ok=True)
        return full_path

    def route(self, doc_meta: dict) -> RouteDecision:
        confidence = float(doc_meta.get("confidence") or 0.0)
        needs_review = bool(doc_meta.get("needs_review", True))
        path_exists = bool(doc_meta.get("path_exists", False))
        signal_count = int(doc_meta.get("signal_count") or 0)
        sensitive = self.is_sensitive(doc_meta)

        if sensitive:
            return RouteDecision(
                action="pending_review",
                destination=self.pending_dir,
                reason="sensitive document — always pending review",
                sensitive=True,
                confidence=confidence,
            )

        # AUTO-FILE: 3 conditions must hold
        # 1. confidence >= 0.90
        # 2. at least 2 independent signals (doctype + content or entity)
        # 3. not flagged needs_review
        # Subfolder is created if it doesn't exist — root must be a valid vault root.
        if (confidence >= AUTO_FILE_CONFIDENCE
                and signal_count >= 2
                and not needs_review):
            dest = self.resolve_destination(
                doc_meta.get("suggested_destination"),
                doc_meta.get("suggested_project"),
            )
            if dest is not None:
                return RouteDecision(
                    action="auto_file",
                    destination=dest,
                    reason=(
                        f"confidence {confidence:.2f} >= {AUTO_FILE_CONFIDENCE}, "
                        f"signal_count={signal_count}, not needs_review"
                    ),
                    sensitive=False,
                    confidence=confidence,
                )

        # PENDING STRONG: confident with valid root but single signal or needs_review
        if confidence >= PENDING_STRONG_CONFIDENCE:
            return RouteDecision(
                action="pending_strong",
                destination=self.pending_dir,
                reason=(
                    f"confidence {confidence:.2f} >= {PENDING_STRONG_CONFIDENCE}, "
                    f"signal_count={signal_count} or needs_review={needs_review}"
                ),
                sensitive=False,
                confidence=confidence,
            )

        return RouteDecision(
            action="pending_review",
            destination=self.pending_dir,
            reason=(
                f"confidence={confidence:.2f}, path_exists={path_exists}, "
                f"signal_count={signal_count}, needs_review={needs_review}"
            ),
            sensitive=False,
            confidence=confidence,
        )
