import re
from pathlib import Path
from typing import Optional


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


def ensure_upload_directory(upload_dir: str | Path | None = None) -> Path:
    base_dir = Path(upload_dir) if upload_dir else Path(__file__).resolve().parent / "static" / "uploads"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def _build_safe_filename(filename: str) -> str:
    name = Path(filename).name
    safe_name = re.sub(r'[^A-Za-z0-9._-]+', '-', name).strip('._-')
    return safe_name or "upload"


def save_uploaded_file(file_bytes: bytes, filename: str, upload_dir: str | Path | None = None) -> Optional[str]:
    if not file_bytes:
        return None

    target_dir = ensure_upload_directory(upload_dir)
    target_path = target_dir / _build_safe_filename(filename)
    counter = 1

    while target_path.exists():
        stem = target_path.stem
        suffix = target_path.suffix
        target_path = target_dir / f"{stem}-{counter}{suffix}"
        counter += 1

    target_path.write_bytes(file_bytes)
    return str(target_path)


def build_media_url(file_path: str | Path) -> str:
    file_path = Path(file_path)
    static_root = Path(__file__).resolve().parent / "static"
    try:
        relative_path = file_path.relative_to(static_root)
    except ValueError:
        relative_path = Path(file_path.name)
    return f"/static/{relative_path.as_posix()}"


def delete_uploaded_file(file_path: str | Path | None) -> bool:
    if not file_path:
        return False

    path = Path(file_path)
    if not path.exists():
        return False

    try:
        path.unlink()
        return True
    except OSError:
        return False


def is_allowed_media_type(content_type: str | None) -> bool:
    if not content_type:
        return False

    normalized = content_type.split(";", 1)[0].lower()
    allowed_prefixes = ("image/", "video/", "audio/", "application/pdf")
    return normalized.startswith(allowed_prefixes)
