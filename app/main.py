"""FastAPI service: Thai TTS via edge-tts.

Voices:
  male   -> th-TH-NiwatNeural
  female -> th-TH-PremwadeeNeural

Note: edge-tts does NOT support mood/tone (style/role) for Thai neural
voices, so the payload only exposes speed and pitch.
"""

import io

import edge_tts
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

VOICES = {
    "male": "th-TH-NiwatNeural",
    "female": "th-TH-PremwadeeNeural",
}

TTS_SECRET = "kuyG1bW3qnG5ofoUQOM"


def verify_secret(x_tts_secret: str = Header(...)) -> None:
    if x_tts_secret != TTS_SECRET:
        raise HTTPException(status_code=401, detail="Invalid secret")


app = FastAPI(title="Thai Edge-TTS", version="1.0.0")


class TTSRequest(BaseModel):
    text: str = Field(
        ..., min_length=1, max_length=5000, description="Thai text to speak"
    )
    gender: str = Field(..., pattern="^(male|female)$")
    speed: float = Field(
        0.5, ge=0.0, le=1.0, description="0=slowest, 0.5=normal, 1=fastest"
    )
    pitch: float = Field(
        0.5, ge=0.0, le=1.0, description="0=lowest, 0.5=normal, 1=highest"
    )


def _rate(speed: float) -> str:
    pct = round((speed - 0.5) * 100)
    return f"{pct:+d}%"


def _pitch(pitch: float) -> str:
    hz = round((pitch - 0.5) * 100)
    return f"{hz:+d}Hz"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/", dependencies=[Depends(verify_secret)])
async def tts(req: TTSRequest):
    voice = VOICES[req.gender]
    communicate = edge_tts.Communicate(
        req.text,
        voice,
        rate=_rate(req.speed),
        pitch=_pitch(req.pitch),
    )

    buf = io.BytesIO()
    try:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc

    if buf.tell() == 0:
        raise HTTPException(status_code=502, detail="No audio generated")

    buf.seek(0)
    return StreamingResponse(buf, media_type="audio/mpeg")
