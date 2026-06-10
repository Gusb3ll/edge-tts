"""Helpers for the macOS `say` (Siri) endpoint."""

import os
import re
import subprocess
import tempfile
import unicodedata
from xml.sax.saxutils import escape

# macOS `say` voice used for the Siri endpoint.
SIRI_VOICE = "Kanya"

# Thai combining marks (tone marks, above/below vowels, repetition sign)
# that must never start a new chunk, or `say` mangles the cluster.
THAI_COMBINING = "ัิีึืุูํ็่้๊๋ๆ"

# Allowed SSML <prosody> values (W3C SSML 1.1 §3.2.4). pitch & range take
# labels / Hz / semitones / relative / percent; rate takes labels or a
# non-negative percentage. Whitelisting also blocks SSML injection since
# the value is interpolated into a quoted attribute.
_NUM = r"[+-]?\d+(?:\.\d+)?"
PITCH_RANGE_RE = re.compile(
    rf"^(?:x-low|low|medium|high|x-high|default|{_NUM}(?:Hz|st|%))$"
)
RATE_RE = re.compile(r"^(?:x-slow|slow|medium|fast|x-fast|default|\d+(?:\.\d+)?%)$")


def build_prosody(
    text: str,
    pitch: str | None = None,
    range_: str | None = None,
    rate: str | None = None,
) -> str:
    """Wrap text in SSML, applying validated <prosody> attributes.

    Raises ValueError on a value that does not match the SSML grammar.
    """
    attrs = []
    for name, value, pattern in (
        ("pitch", pitch, PITCH_RANGE_RE),
        ("range", range_, PITCH_RANGE_RE),
        ("rate", rate, RATE_RE),
    ):
        if value is None:
            continue
        if not pattern.match(value):
            raise ValueError(f"invalid {name} value: {value!r}")
        attrs.append(f"{name}='{value}'")

    inner = escape(text)
    if not attrs:
        return f"<speak>{inner}</speak>"
    return f"<speak><prosody {' '.join(attrs)}>{inner}</prosody></speak>"


def chunk_text(text: str, size: int = 40):
    """Split text into <=~size-char pieces at safe boundaries.

    The macOS `say` Thai voice truncates long inputs that contain
    malformed grapheme clusters, emitting only the first word. Feeding
    it shorter chunks dodges the bug. We only break before a base
    (non-combining) character so clusters stay intact.
    """
    chunks, cur = [], ""
    for ch in text:
        if (
            len(cur) >= size
            and not unicodedata.combining(ch)
            and ch not in THAI_COMBINING
        ):
            chunks.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        chunks.append(cur)
    return chunks


def say_wav(text: str) -> bytes:
    """Synthesize one chunk via `say` to 16-bit 22.05kHz mono WAV bytes.

    Speech rate is carried in the SSML <prosody rate>, not the -r flag.
    """
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        subprocess.run(
            [
                "say",
                "-v",
                SIRI_VOICE,
                "--file-format=WAVE",
                "--data-format=LEI16@22050",
                "-o",
                path,
                text,
            ],
            check=True,
            capture_output=True,
        )
        with open(path, "rb") as f:
            return f.read()
    finally:
        os.unlink(path)
