import os
from dataclasses import dataclass, field

VAULT_ROOT = "/home/leo-paz/obsidian-vault"

ALLOWED_ROOTS = [
    "00 - Command",
    "10 - BBS",
    "20 - ClawBot",
    "30 - AI Systems",
    "40 - Ventures",
    "50 - Career",
    "60 - Personal",
    "70 - Household",
    "99 - Archive",
]

VALID_DOC_TYPES = {
    "receipt", "invoice", "contract", "report", "form",
    "plan", "SOP", "note", "research", "email", "other"
}


@dataclass
class ClassificationResult:
    document_type: str          # receipt|invoice|contract|report|form|plan|SOP|note|research|email|other
    root: str                   # one of the 9 vault roots e.g. "60 - Personal"
    relative_path: str          # same as root — never an invented subfolder
    suggested_subfolder: str    # advisory only, may be ""
    path_exists: bool           # True if suggested_subfolder exists on disk (or no subfolder)
    confidence: float
    reason: str
    evidence: list
    signal_count: int           # independent signals: doctype + content + entity (max 1 each)
    needs_review: bool
    tags: list
    method: str
    summary: str = ""


def _subfolder_exists(root: str, subfolder: str) -> bool:
    if not root:
        return False
    if not subfolder:
        return os.path.isdir(os.path.join(VAULT_ROOT, root))
    return os.path.isdir(os.path.join(VAULT_ROOT, root, subfolder))


class RulesClassifier:

    def classify(self, text: str, filename: str) -> ClassificationResult:
        try:
            return self._classify(text, filename)
        except Exception:
            return ClassificationResult(
                document_type="other", root="", relative_path="", suggested_subfolder="",
                path_exists=False, confidence=0.0, reason="rules classifier exception",
                evidence=[], signal_count=0, needs_review=True, tags=[], method="rules",
            )

    def _classify(self, text: str, filename: str) -> ClassificationResult:
        fn = filename.lower()
        tx = text.lower()

        # ---------------------------------------------------------------
        # Filename-based rules — 2 signals (doctype + filename keyword)
        # ---------------------------------------------------------------

        if "resume" in fn or ("cv" in fn and fn.endswith((".txt", ".docx", ".pdf"))):
            root = "50 - Career"
            sub = "Resume"
            return ClassificationResult(
                document_type="other",
                root=root, relative_path=root, suggested_subfolder=sub,
                path_exists=_subfolder_exists(root, sub),
                confidence=0.95, reason="filename indicates resume/CV",
                evidence=["filename:resume_or_cv", "doctype:career_document"],
                signal_count=2, needs_review=False,
                tags=["resume", "career"], method="rules",
            )

        if "sop" in fn or "standard operating" in fn:
            root = "10 - BBS"
            sub = "SOPs"
            return ClassificationResult(
                document_type="SOP",
                root=root, relative_path=root, suggested_subfolder=sub,
                path_exists=_subfolder_exists(root, sub),
                confidence=0.90, reason="filename indicates standard operating procedure",
                evidence=["filename:sop", "doctype:SOP"],
                signal_count=2, needs_review=False,
                tags=["sop", "process"], method="rules",
            )

        if any(w in fn for w in ("paystatement", "pay statement", "pay stub", "paystub")):
            root = "60 - Personal"
            sub = "Finance"
            return ClassificationResult(
                document_type="receipt",
                root=root, relative_path=root, suggested_subfolder=sub,
                path_exists=_subfolder_exists(root, sub),
                confidence=0.90, reason="filename indicates pay stub",
                evidence=["filename:paystub", "doctype:receipt"],
                signal_count=2, needs_review=True,
                tags=["finance", "payroll"], method="rules",
            )

        # ---------------------------------------------------------------
        # Content-based rules with document type signal (2 signals)
        # ---------------------------------------------------------------

        # Payroll: strong content keyword cluster + doctype inference
        if (any(w in tx for w in ("net pay", "gross pay", "federal income tax", "social security"))
                and "earnings" in tx):
            root = "60 - Personal"
            sub = "Finance"
            return ClassificationResult(
                document_type="receipt",
                root=root, relative_path=root, suggested_subfolder=sub,
                path_exists=_subfolder_exists(root, sub),
                confidence=0.90, reason="payroll keyword cluster: net pay, gross pay, earnings",
                evidence=["keywords:payroll_cluster", "doctype:receipt"],
                signal_count=2, needs_review=True,
                tags=["finance", "payroll"], method="rules",
            )

        # ---------------------------------------------------------------
        # Named entity rules — 1 signal only, confidence capped at 0.45
        # (below LLM fallback threshold of 0.50, so LLM always runs next)
        # ---------------------------------------------------------------

        if "beacon bridge" in tx or " bbs " in tx:
            root = "10 - BBS"
            return ClassificationResult(
                document_type="other",
                root=root, relative_path=root, suggested_subfolder="",
                path_exists=_subfolder_exists(root, ""),
                confidence=0.45, reason="entity match: Beacon Bridge Strategies",
                evidence=["entity:beacon_bridge"],
                signal_count=1, needs_review=True,
                tags=["bbs"], method="rules",
            )

        if "clawbot" in tx or "openclaw" in tx or "cron job" in tx:
            root = "20 - ClawBot"
            return ClassificationResult(
                document_type="other",
                root=root, relative_path=root, suggested_subfolder="",
                path_exists=_subfolder_exists(root, ""),
                confidence=0.45, reason="entity match: ClawBot / OpenClaw",
                evidence=["entity:clawbot"],
                signal_count=1, needs_review=True,
                tags=["clawbot"], method="rules",
            )

        if "agent os" in tx:
            root = "30 - AI Systems"
            return ClassificationResult(
                document_type="other",
                root=root, relative_path=root, suggested_subfolder="Agent OS",
                path_exists=_subfolder_exists(root, "Agent OS"),
                confidence=0.45, reason="entity match: Agent OS",
                evidence=["entity:agent_os"],
                signal_count=1, needs_review=True,
                tags=["agent-os"], method="rules",
            )

        if "siftwise" in tx:
            root = "40 - Ventures"
            return ClassificationResult(
                document_type="other",
                root=root, relative_path=root, suggested_subfolder="Siftwise",
                path_exists=_subfolder_exists(root, "Siftwise"),
                confidence=0.45, reason="entity match: Siftwise",
                evidence=["entity:siftwise"],
                signal_count=1, needs_review=True,
                tags=["siftwise"], method="rules",
            )

        if "farah" in tx and any(w in tx for w in ("talent", "content", "ugc", "brand")):
            root = "40 - Ventures"
            return ClassificationResult(
                document_type="other",
                root=root, relative_path=root, suggested_subfolder="",
                path_exists=_subfolder_exists(root, ""),
                confidence=0.45, reason="entity match: Farah + talent/content keywords",
                evidence=["entity:farah", "keyword:talent_brand"],
                signal_count=1, needs_review=True,
                tags=["farah", "talent"], method="rules",
            )

        if "farah" in tx and any(w in tx for w in ("family", "personal")):
            root = "60 - Personal"
            return ClassificationResult(
                document_type="other",
                root=root, relative_path=root, suggested_subfolder="",
                path_exists=_subfolder_exists(root, ""),
                confidence=0.45, reason="entity match: Farah + personal/family context",
                evidence=["entity:farah", "keyword:family_personal"],
                signal_count=1, needs_review=True,
                tags=["farah", "personal"], method="rules",
            )

        if "mirage" in tx and any(w in tx for w in ("dealership", "dealer", "boa-franc", "d365")):
            root = "50 - Career"
            return ClassificationResult(
                document_type="other",
                root=root, relative_path=root, suggested_subfolder="",
                path_exists=_subfolder_exists(root, ""),
                confidence=0.45, reason="entity match: Mirage + career keywords",
                evidence=["entity:mirage", "keyword:career_context"],
                signal_count=1, needs_review=True,
                tags=["mirage", "career"], method="rules",
            )

        # No match
        return ClassificationResult(
            document_type="other", root="", relative_path="", suggested_subfolder="",
            path_exists=False, confidence=0.0, reason="no rules matched",
            evidence=[], signal_count=0, needs_review=True, tags=[], method="rules",
        )
