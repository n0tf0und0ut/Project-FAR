"""Optional operator-controlled local media/PDF intake.

No automatic speech transcription is claimed. Audio/video requires separate
provider authorization; source confidence and speaker/time attribution unknown.
"""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import tempfile
from acquire import AcquisitionError
from engine import digest

MAX_LOCAL_FILE = 100_000_000
MAX_PDF = 8_000_000
MAX_TRANSCRIPTION_AUDIO = 24_000_000


def read_pdf(path: Path) -> dict:
    if path.stat().st_size > MAX_PDF:
        raise AcquisitionError("PDF file exceeds 8 MB cap")
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise AcquisitionError("pypdf optional dependency unavailable") from exc
    try:
        with path.open("rb") as f:
            reader = PdfReader(f, strict=True)
            if reader.is_encrypted:
                raise AcquisitionError("encrypted PDF not supported")
            if not 1 <= len(reader.pages) <= 30:
                raise AcquisitionError("PDF page count out of range")
            pages = []
            for page in reader.pages:
                chunk = page.extract_text() or ""
                pages.append(chunk)
    except AcquisitionError:
        raise
    except Exception as exc:
        raise AcquisitionError("PDF extraction failed") from exc
    text = "\n\n".join(pages).strip()
    if not text:
        raise AcquisitionError("PDF has no extractable text; OCR not implemented")
    if len(text.encode("utf-8")) > 190_000:
        raise AcquisitionError("extracted PDF text too large")
    return {"text": text, "extraction": "pypdf_text_v1", "pages": len(pages),
            "raw_sha256": digest(path.read_bytes()), "external_authenticity_verified": False,
            "visual_figure_and_table_fidelity_verified": False}


def transcribe_local(path: Path, *, permit_model: bool = False, client=None,
                     converter="ffmpeg") -> dict:
    if not permit_model:
        raise AcquisitionError("audio transcription needs explicit external-model authorization")
    if path.suffix.lower() not in {".mp3", ".wav", ".m4a", ".mp4", ".mov", ".webm", ".ogg"}:
        raise AcquisitionError("unsupported local media extension")
    if not 0 < path.stat().st_size <= MAX_LOCAL_FILE:
        raise AcquisitionError("media file size over limit")
    with tempfile.TemporaryDirectory(prefix="far-media-") as root:
        output = Path(root) / "mono.mp3"
        cmd = [converter, "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", str(path),
               "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", "-t", "1800", str(output)]
        try:
            # No shell, no browser, no dynamic model-generated command.
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=100, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AcquisitionError("ffmpeg unavailable or timed out") from exc
        if proc.returncode != 0 or not output.is_file():
            raise AcquisitionError("media conversion failed")
        if not 0 < output.stat().st_size <= MAX_TRANSCRIPTION_AUDIO:
            raise AcquisitionError("converted audio exceeds provider file cap")
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise AcquisitionError("OpenAI SDK not installed") from exc
            client = OpenAI(timeout=40, max_retries=0)
        try:
            with output.open("rb") as f:
                result = client.audio.transcriptions.create(model="gpt-4o-transcribe", file=f,
                                                              response_format="json")
            text = getattr(result, "text", None)
            if not isinstance(text, str) or not text.strip():
                raise AcquisitionError("transcription provider returned no text")
        except AcquisitionError:
            raise
        except Exception as exc:
            raise AcquisitionError("transcription provider request failed") from exc
        if len(text.encode("utf-8")) > 190_000:
            raise AcquisitionError("transcript exceeds text cap")
        return {"text": text, "extraction": "external_speech_transcription_gpt4o_v1",
                "raw_sha256": digest(path.read_bytes()), "transcript_model": "gpt-4o-transcribe",
                "transcript_alignment_verified": False, "speaker_attribution_verified": False,
                "external_authenticity_verified": False}


def read_local_file(kind: str, path: str, *, permit_model: bool = False, transcription_client=None) -> dict:
    p = Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size > MAX_LOCAL_FILE:
        raise AcquisitionError("file missing, symlink or oversized")
    if kind == "pdf_file":
        if p.suffix.lower() != ".pdf":
            raise AcquisitionError("PDF source requires .pdf extension")
        return read_pdf(p)
    if kind == "media_file":
        return transcribe_local(p, permit_model=permit_model, client=transcription_client)
    raise AcquisitionError("local file kind unsupported")
