import json
import os
import re
import urllib.request
import urllib.error
from dataclasses import dataclass, field

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = os.environ.get("INGEST_LLM_MODEL", "qwen3:14b")

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


@dataclass
class SummaryResult:
    success: bool
    summary: str
    document_type: str          # receipt|invoice|contract|report|form|plan|SOP|note|research|email|other
    root: str                   # one of the 9 allowed vault roots
    relative_path: str          # same as root
    suggested_subfolder: str    # advisory only
    path_exists: bool
    reason: str
    evidence: list
    needs_review: bool
    key_facts: list
    action_items: list
    tags: list
    entities: list
    risks: list
    confidence: float
    model: str
    input_chars: int
    output_chars: int
    error_message: str = ""
    # Backward-compat aliases consumed by LLMClassifier
    suggested_project: str = ""
    suggested_destination: str = ""


_VAULT_ROOTS_WITH_DESC = """  00 - Command  — agent governance, policy, soul, operating doctrine
  10 - BBS  — Beacon Bridge Strategies consulting: client research, outreach, med spa, capability statements
  20 - ClawBot  — ClawBot dashboard, cron jobs, ingest pipeline, agent workflows, execution logs
  30 - AI Systems  — AI architecture, Agent OS, OpenClaw, LLM model stack, multi-agent design
  40 - Ventures  — Side businesses and ventures outside BBS: RankBeacon, startups, product ideas
  50 - Career  — W-2 career: Mirage, Boa-Franc, D365, dealership, resumes, job applications
  60 - Personal  — Personal docs: finance, receipts, bank statements, medical, school forms, family
  70 - Household  — House, property, maintenance, utilities, rental, Palm Bay
  99 - Archive  — Archived or rejected material only"""

_PROMPT_TEMPLATE = (
    "You are a document router. Your job is to determine what a document IS and where it belongs "
    "in a known vault structure.\n"
    "\n"
    "Step 1: Determine document type. Choose one:\n"
    "  receipt, invoice, contract, report, form, plan, SOP, note, research, email, other\n"
    "\n"
    "Step 2: Choose exactly one vault root from this list (read the descriptions carefully):\n"
    "{allowed_roots}\n"
    "\n"
    "Step 3: Optionally suggest a subfolder. This is advisory only. Do not invent paths that do "
    "not exist. Use simple folder names like Finance/Receipts or Market Research/Med Spas.\n"
    "\n"
    "Rules:\n"
    "- Named entities (people, companies, projects) are evidence, not destination deciders.\n"
    "- A receipt is a receipt even if it mentions a project name.\n"
    "- Choose the root that matches what the document IS, not what it mentions.\n"
    "- 10 - BBS covers anything related to Beacon Bridge Strategies or consulting for clients.\n"
    "- 60 - Personal covers personal finance, receipts, school forms, family documents.\n"
    "- 99 - Archive is ONLY for items explicitly marked as old or rejected — do not use it for current documents.\n"
    "- If you are unsure between two roots, pick the more specific one and lower your confidence.\n"
    "- Confidence reflects how certain you are about the root assignment, not the subfolder.\n"
    "- If no root clearly fits, set confidence below 0.70 and needs_review to true.\n"
    "\n"
    "Document filename: {filename}\n"
    "Document type hint: {file_type}\n"
    "\n"
    "Respond with this exact JSON structure. No preamble. No explanation. No markdown fences.\n"
    '{{\n'
    '  "summary": "2-3 sentence summary of what this document is",\n'
    '  "document_type": "one of the 11 types above",\n'
    '  "root": "one of the 9 vault roots above",\n'
    '  "suggested_subfolder": "advisory subfolder or empty string",\n'
    '  "reason": "one sentence explaining the root assignment",\n'
    '  "evidence": ["entity:NameHere", "content:description here", "doctype:type reason"],\n'
    '  "needs_review": true,\n'
    '  "key_facts": ["fact 1", "fact 2"],\n'
    '  "action_items": ["action 1"],\n'
    '  "tags": ["tag1", "tag2"],\n'
    '  "entities": ["person or org 1"],\n'
    '  "risks": ["risk 1"],\n'
    '  "confidence": 0.0\n'
    '}}\n'
    "\n"
    "Document content:\n"
    "{text}"
)


class LocalLLMSummarizer:

    def __init__(self, model: str = None, timeout: int = 600, max_input_chars: int = 12000):
        self.model = model or DEFAULT_MODEL
        self.timeout = timeout
        self.max_input_chars = max_input_chars

    def summarize(self, text: str, filename: str, file_type: str) -> SummaryResult:
        truncated = text[:self.max_input_chars]
        input_chars = len(truncated)
        prompt = _PROMPT_TEMPLATE.format(
            allowed_roots=_VAULT_ROOTS_WITH_DESC,
            filename=filename,
            file_type=file_type,
            text=truncated,
        )

        try:
            payload = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "format": "json",
            }).encode("utf-8")
            req = urllib.request.Request(
                OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except Exception as exc:
            return self._fail(input_chars, f"HTTP error: {exc}")

        try:
            api_resp = json.loads(raw)
            response_text = api_resp.get("response", "")
            response_text = self._clean_response(response_text)
            output_chars = len(response_text)
            parsed = json.loads(response_text)
        except Exception as exc:
            return self._fail(input_chars, f"Parse error: {exc}")

        root = parsed.get("root", "")
        if root not in ALLOWED_ROOTS:
            root = self._nearest_root(root)

        subfolder = parsed.get("suggested_subfolder", "") or ""
        relative_path = root

        from classifiers.rules_classifier import _subfolder_exists
        path_exists = _subfolder_exists(root, subfolder) if root else False

        doc_type = parsed.get("document_type", "other") or "other"
        from classifiers.rules_classifier import VALID_DOC_TYPES
        if doc_type not in VALID_DOC_TYPES:
            doc_type = "other"

        return SummaryResult(
            success=True,
            summary=parsed.get("summary", ""),
            document_type=doc_type,
            root=root,
            relative_path=relative_path,
            suggested_subfolder=subfolder,
            path_exists=path_exists,
            reason=parsed.get("reason", ""),
            evidence=parsed.get("evidence", []),
            needs_review=bool(parsed.get("needs_review", True)),
            key_facts=parsed.get("key_facts", []),
            action_items=parsed.get("action_items", []),
            tags=parsed.get("tags", []),
            entities=parsed.get("entities", []),
            risks=parsed.get("risks", []),
            confidence=float(parsed.get("confidence", 0.0)),
            model=self.model,
            input_chars=input_chars,
            output_chars=output_chars,
            suggested_project=root,
            suggested_destination=relative_path,
        )

    def _fail(self, input_chars: int, error: str) -> SummaryResult:
        return SummaryResult(
            success=False,
            summary="", document_type="other", root="", relative_path="",
            suggested_subfolder="", path_exists=False, reason="", evidence=[],
            needs_review=True, key_facts=[], action_items=[], tags=[], entities=[],
            risks=[], confidence=0.0, model=self.model,
            input_chars=input_chars, output_chars=0, error_message=error,
            suggested_project="", suggested_destination="",
        )

    def _nearest_root(self, raw: str) -> str:
        if not raw:
            return ""
        raw_lower = raw.lower()
        for r in ALLOWED_ROOTS:
            if r.lower() in raw_lower or raw_lower in r.lower():
                return r
        return ""

    def _clean_response(self, text: str) -> str:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text
