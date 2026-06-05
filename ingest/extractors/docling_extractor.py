import os
import sys

# Resolved at module load time — safe, no circular dependency.
# The actual import of ExtractedDocument is deferred into the function body
# so that ingest.py is fully initialized before we reach that line.
_INGEST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _docling_version() -> str:
    try:
        from importlib.metadata import version
        return version("docling")
    except Exception:
        return "unknown"


def extract_docling(file_path: str):
    if _INGEST_DIR not in sys.path:
        sys.path.insert(0, _INGEST_DIR)
    from ingest import ExtractedDocument

    ext = os.path.splitext(file_path)[1].lower()
    extractor_name = f"docling-{_docling_version()}"
    try:
        from docling.document_converter import DocumentConverter
        converter = DocumentConverter()
        result = converter.convert(file_path)
        doc = result.document
        text = doc.export_to_markdown()
        try:
            page_count = len(doc.pages)
        except Exception:
            page_count = None
        metadata = {"page_count": page_count, "extractor_version": _docling_version()}
        return ExtractedDocument(
            input_path=file_path,
            file_type=ext,
            success=True,
            extracted_text=text,
            metadata=metadata,
            extractor_name=extractor_name,
            char_count=len(text),
        )
    except Exception as exc:
        return ExtractedDocument(
            input_path=file_path,
            file_type=ext,
            success=False,
            extracted_text="",
            metadata={},
            extractor_name=extractor_name,
            char_count=0,
            error_message=str(exc),
        )
