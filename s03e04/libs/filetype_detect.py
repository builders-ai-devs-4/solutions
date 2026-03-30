from pathlib import Path
import mimetypes
from dataclasses import dataclass

@dataclass
class FileDetection:
    path: Path
    extension: str | None
    # MIME guessed from file name/extension (mimetypes module)
    mime_from_name: str | None
    # MIME inferred from header signature (magic bytes)
    kind_from_magic: str | None
    # Heuristic flag: does the file content look like text?
    looks_like_text: bool
    # Normalized final category used by your pipeline
    final_kind: str
    # Confidence of detection: high/medium/low
    confidence: str

# Common magic-byte signatures for popular file formats.
# Detection priority is based on raw bytes, so it is harder to spoof than extension.
MAGIC_SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"%PDF-", "application/pdf"),
    (b"PK\x03\x04", "application/zip"),   # zip, docx, xlsx, pptx...
    (b"RIFF", "audio/wav_or_webp"),       # for RIFF but not enough to distinguish WAV vs WEBP
    (b"ID3", "audio/mpeg"),
]

# Manual extension-to-MIME mapping for selected formats.
# Useful when mimetypes is missing or inconsistent on a given OS.
EXT_TO_MIME = {
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".log": "text/plain",
    ".json": "application/json",
    ".csv": "text/csv",
    ".xml": "application/xml",
    ".html": "text/html",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}

def looks_like_text_bytes(sample: bytes) -> bool:
    # Empty sample is treated as text-like (for example, empty file)
    if not sample:
        return True
    # Null byte usually indicates binary content
    if b"\x00" in sample:
        return False
    try:
        decoded = sample.decode("utf-8")
    except UnicodeDecodeError:
        return False

    # Ratio of printable chars helps separate text from binary noise
    printable = sum(ch.isprintable() or ch in "\n\r\t" for ch in decoded)
    ratio = printable / max(len(decoded), 1)
    return ratio > 0.9

def detect_magic(header: bytes) -> str | None:
    # Match file header against known signatures
    for sig, kind in MAGIC_SIGNATURES:
        if header.startswith(sig):
            if kind == "audio/wav_or_webp":
                # RIFF container can represent WAV or WEBP
                if len(header) >= 12 and header[8:12] == b"WAVE":
                    return "audio/wav"
                if len(header) >= 12 and header[8:12] == b"WEBP":
                    return "image/webp"
            return kind
    return None

def normalize_kind(mime: str | None, looks_text: bool) -> str:
    # Convert detailed MIME to a simpler category used by downstream logic
    if mime:
        if mime.startswith("image/"):
            return "image"
        if mime.startswith("text/"):
            return "text"
        if mime.startswith("audio/"):
            return "audio"
        if mime in {"application/json", "application/xml", "application/pdf", "application/zip"}:
            return mime
    # Fallback category when MIME is unknown
    return "text" if looks_text else "binary"

def detect_file_type(path: str | Path, sample_size: int = 4096) -> FileDetection:
    p = Path(path)
    ext = p.suffix.lower() if p.suffix else None
    mime_from_name, _ = mimetypes.guess_type(str(p))
    # Fallback to manual mapping if mimetypes did not return anything
    if not mime_from_name and ext in EXT_TO_MIME:
        mime_from_name = EXT_TO_MIME[ext]

    # Read only a small header chunk for quick detection
    with p.open("rb") as f:
        header = f.read(sample_size)

    # Signature-based detection is the most reliable signal here
    kind_from_magic = detect_magic(header)
    # Heuristic fallback for unknown formats
    text_like = looks_like_text_bytes(header)

    # Priority: magic bytes > extension/MIME guess > text/binary heuristic
    chosen_mime = kind_from_magic or mime_from_name
    final_kind = normalize_kind(chosen_mime, text_like)

    # Confidence reflects which signal was used
    if kind_from_magic:
        confidence = "high"
    elif mime_from_name:
        confidence = "medium"
    else:
        confidence = "low"

    return FileDetection(
        path=p,
        extension=ext,
        mime_from_name=mime_from_name,
        kind_from_magic=kind_from_magic,
        looks_like_text=text_like,
        final_kind=final_kind,
        confidence=confidence,
    )