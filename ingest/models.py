from dataclasses import dataclass


@dataclass
class ExtractedDocument:
    input_path: str
    file_type: str
    success: bool
    extracted_text: str
    metadata: dict
    extractor_name: str
    char_count: int
    error_message: str = ""