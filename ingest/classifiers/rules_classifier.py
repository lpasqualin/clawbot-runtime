from dataclasses import dataclass


@dataclass
class ClassificationResult:
    project: str
    destination: str
    content_type: str
    tags: list
    confidence: float
    method: str


class RulesClassifier:

    def classify(self, text: str, filename: str) -> ClassificationResult:
        try:
            fn = filename.lower()
            tx = text.lower()

            # Filename rules — first match wins
            if "resume" in fn or "cv" in fn:
                return ClassificationResult(
                    project="Career",
                    destination="50 - Career/Resume/",
                    content_type="resume",
                    tags=["resume", "career"],
                    confidence=0.95,
                    method="rules",
                )
            if "sop" in fn or "standard operating" in fn:
                return ClassificationResult(
                    project="BBS",
                    destination="20 - BBS/SOPs/",
                    content_type="sop",
                    tags=["sop", "process"],
                    confidence=0.90,
                    method="rules",
                )

            # Text rules — first match wins
            if "beacon bridge" in tx or " bbs" in tx:
                return ClassificationResult(
                    project="BBS",
                    destination="20 - BBS/",
                    content_type="business",
                    tags=["bbs"],
                    confidence=0.85,
                    method="rules",
                )
            if "clawbot" in tx or "openclaw" in tx or "cron job" in tx:
                return ClassificationResult(
                    project="ClawBot",
                    destination="30 - ClawBot/",
                    content_type="technical",
                    tags=["clawbot"],
                    confidence=0.85,
                    method="rules",
                )
            if "siftwise" in tx:
                return ClassificationResult(
                    project="Siftwise",
                    destination="60 - Projects/Siftwise/",
                    content_type="technical",
                    tags=["siftwise"],
                    confidence=0.85,
                    method="rules",
                )
            if "farah" in tx and any(w in tx for w in ("talent", "content", "ugc", "brand")):
                return ClassificationResult(
                    project="Farah",
                    destination="40 - Ventures/Starlight-Talent/",
                    content_type="business",
                    tags=["farah", "talent"],
                    confidence=0.80,
                    method="rules",
                )
            if "farah" in tx and any(w in tx for w in ("family", "personal")):
                return ClassificationResult(
                    project="Personal",
                    destination="60 - Personal/Farah/",
                    content_type="personal",
                    tags=["farah", "personal"],
                    confidence=0.80,
                    method="rules",
                )
            if "agent os" in tx:
                return ClassificationResult(
                    project="Agent OS",
                    destination="30 - ClawBot/Agent OS/",
                    content_type="technical",
                    tags=["agent-os"],
                    confidence=0.85,
                    method="rules",
                )

            return ClassificationResult(
                project="",
                destination="",
                content_type="unknown",
                tags=[],
                confidence=0.0,
                method="rules",
            )
        except Exception:
            return ClassificationResult(
                project="",
                destination="",
                content_type="unknown",
                tags=[],
                confidence=0.0,
                method="rules",
            )
