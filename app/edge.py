"""Helpers for the edge-tts endpoint."""


def edge_rate(speed: float) -> str:
    """edge-tts rate string. 0=-50%, 0.5=+0%, 1=+50%."""
    pct = round((speed - 0.5) * 100)
    return f"{pct:+d}%"


def edge_pitch(pitch: float) -> str:
    """edge-tts pitch string. 0=-50Hz, 0.5=+0Hz, 1=+50Hz."""
    hz = round((pitch - 0.5) * 100)
    return f"{hz:+d}Hz"
