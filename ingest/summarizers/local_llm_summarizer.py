import json
import os
import re
import urllib.request
import urllib.error
from dataclasses import dataclass

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = os.environ.get("INGEST_LLM_MODEL", "qwen3:14b")


@dataclass
class SummaryResult:
    success: bool
    summary: str
    key_facts: list
    action_items: list
    suggested_project: str
    suggested_destination: str
    tags: list
    entities: list
    risks: list
    confidence: float
    model: str
    input_chars: int
    output_chars: int
    error_message: str = ""


_PROMPT_TEMPLATE = (
    "You are a document classifier and summarizer. Analyze the document below and\n"
    "respond with a JSON object only. No preamble. No explanation. No markdown fences.\n"
    "\n"
    "Document filename: {filename}\n"
    "Document type: {file_type}\n"
    "\n"
    "Respond with this exact JSON structure:\n"
    '{{\n'
    '  "summary": "2-3 sentence summary of what this document is",\n'
    '  "key_facts": ["fact 1", "fact 2"],\n'
    '  "action_items": ["action 1", "action 2"],\n'
    '  "suggested_project": "one of: BBS, ClawBot, Career, Farah, Siftwise, Agent OS, Personal, Unknown",\n'
    '  "suggested_destination": "vault subfolder path suggestion",\n'
    '  "tags": ["tag1", "tag2"],\n'
    '  "entities": ["person or org name 1", "person or org name 2"],\n'
    '  "risks": ["risk or open question 1"],\n'
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
            return SummaryResult(
                success=False,
                summary="",
                key_facts=[],
                action_items=[],
                suggested_project="",
                suggested_destination="",
                tags=[],
                entities=[],
                risks=[],
                confidence=0.0,
                model=self.model,
                input_chars=input_chars,
                output_chars=0,
                error_message=f"HTTP error: {exc}",
            )

        try:
            api_resp = json.loads(raw)
            response_text = api_resp.get("response", "")
            response_text = self._clean_response(response_text)
            output_chars = len(response_text)
            parsed = json.loads(response_text)
        except Exception as exc:
            return SummaryResult(
                success=False,
                summary="",
                key_facts=[],
                action_items=[],
                suggested_project="",
                suggested_destination="",
                tags=[],
                entities=[],
                risks=[],
                confidence=0.0,
                model=self.model,
                input_chars=input_chars,
                output_chars=0,
                error_message=f"Parse error: {exc}",
            )

        return SummaryResult(
            success=True,
            summary=parsed.get("summary", ""),
            key_facts=parsed.get("key_facts", []),
            action_items=parsed.get("action_items", []),
            suggested_project=parsed.get("suggested_project", ""),
            suggested_destination=parsed.get("suggested_destination", ""),
            tags=parsed.get("tags", []),
            entities=parsed.get("entities", []),
            risks=parsed.get("risks", []),
            confidence=float(parsed.get("confidence", 0.0)),
            model=self.model,
            input_chars=input_chars,
            output_chars=output_chars,
            error_message="",
        )

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
