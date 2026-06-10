import io
import subprocess
import wave

import edge_tts
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from edge import edge_pitch, edge_rate
from siri import build_prosody, chunk_text, say_wav

EDGETTS_VOICES = {
    "male": "th-TH-NiwatNeural",
    "female": "th-TH-PremwadeeNeural",
}

TTS_SECRET = "kuyG1bW3qnG5ofoUQOM"


def verify_secret(x_tts_secret: str = Header(...)) -> None:
    if x_tts_secret != TTS_SECRET:
        raise HTTPException(status_code=401, detail="Invalid secret")


app = FastAPI()


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


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/generate", dependencies=[Depends(verify_secret)])
async def tts(req: TTSRequest):
    voice = EDGETTS_VOICES[req.gender]
    communicate = edge_tts.Communicate(
        req.text,
        voice,
        rate=edge_rate(req.speed),
        pitch=edge_pitch(req.pitch),
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


class SiriRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="text to speak")
    # Defaults tuned to match the reference voice (~245Hz, brisk tempo).
    pitch: str | None = Field(
        "+21%", description="SSML prosody pitch: label/Hz/st/±/%, e.g. +25%, high, -2st"
    )
    range: str | None = Field(
        None, description="SSML prosody range: label/Hz/st/±/%, e.g. high, +30%"
    )
    rate: str | None = Field(
        "135%", description="SSML prosody rate: label or non-negative %, e.g. 80%, slow"
    )


@app.post("/generate/siri", dependencies=[Depends(verify_secret)])
async def siri(req: SiriRequest):
    try:
        ssml_chunks = [
            build_prosody(chunk, req.pitch, req.range, req.rate)
            for chunk in chunk_text(req.text)
            if chunk.strip()
        ]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    frames = b""
    params = None
    try:
        for ssml in ssml_chunks:
            wav = say_wav(ssml)
            with wave.open(io.BytesIO(wav), "rb") as w:
                if params is None:
                    params = w.getparams()
                frames += w.readframes(w.getnframes())
    except (subprocess.CalledProcessError, OSError) as exc:
        detail = getattr(exc, "stderr", b"") or str(exc)
        if isinstance(detail, bytes):
            detail = detail.decode(errors="replace")
        raise HTTPException(status_code=502, detail=f"say failed: {detail}") from exc

    if not frames or params is None:
        raise HTTPException(status_code=502, detail="No audio generated")

    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setparams(params)
        w.writeframes(frames)
    out.seek(0)
    return StreamingResponse(out, media_type="audio/wav")
