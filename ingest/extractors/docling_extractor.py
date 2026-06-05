import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import ExtractedDocument

try:
    import importlib.metadata
    _docling_version = importlib.metadata.version("docling")
except Exception:
    _docling_version = "unknown"


def extract_docling(file_path: str) -> ExtractedDocument:
    ext = os.path.splitext(file_path)[1].lower()
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions

        if ext == ".pdf":
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = False
            pipeline_options.do_table_structure = True
            converter = DocumentConverter(
                format_options={"pdf": PdfFormatOption(pipeline_options=pipeline_options)}
            )
        else:
            converter = DocumentConverter()

        result = converter.convert(file_path)
        md_text = result.document.export_to_markdown()
        page_count = None
        try:
            page_count = len(result.document.pages)
        except Exception:
            pass
        return ExtractedDocument(
            input_path=file_path,
            file_type=ext,
            success=True,
            extracted_text=md_text,
            metadata={"page_count": page_count, "extractor_version": _docling_version},
            extractor_name=f"docling-{_docling_version}",
            char_count=len(md_text),
            error_message=""
        )
    except Exception as e:
        return ExtractedDocument(
            input_path=file_path,
            file_type=ext,
            success=False,
            extracted_text="",
            metadata={},
            extractor_name=f"docling-{_docling_version}",
            char_count=0,
            error_message=str(e)
        )