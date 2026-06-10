# Thai Edge-TTS API

FastAPI service generating Thai speech with [edge-tts](https://github.com/rany2/edge-tts).

| gender   | voice                  |
|----------|------------------------|
| `male`   | th-TH-NiwatNeural      |
| `female` | th-TH-PremwadeeNeural  |

## Run

```bash
docker compose up --build
```

## Request

`POST /tts` → `audio/mpeg`

```json
{
  "text": "สวัสดีครับ ยินดีต้อนรับ",
  "gender": "male",
  "speed": 0.5,
  "pitch": 0.5
}
```

| field  | range        | meaning                             |
|--------|--------------|-------------------------------------|
| text   | 1–5000 chars | Thai text                           |
| gender | male/female  | voice select                        |
| speed  | 0–1          | 0 slow · 0.5 normal · 1 fast (±50%) |
| pitch  | 0–1          | 0 low · 0.5 normal · 1 high (±50Hz) |

### Mood / tone

Not supported. edge-tts free endpoint exposes no `style`/`role`, and the
Thai neural voices have no expressive styles. Only `speed` and `pitch`
are adjustable. (Mood would require paid Azure Speech with a
style-capable voice — not available for th-TH.)

## Siri voice

`POST /siri` → `audio/mp4` (m4a/AAC) — shells out to the native macOS
`say` command.

> **macOS only.** `say` does not exist on Linux, so this endpoint fails
> inside the Linux Docker image. Run the app natively on a Mac.

```json
{
  "text": "Hello, I am Siri",
  "voice": "Samantha",
  "speed": 0.5
}
```

| field | range        | meaning                               |
|-------|--------------|---------------------------------------|
| text  | 1–5000 chars | text to speak                         |
| voice | `say` voice  | macOS voice name (`say -v ?` to list) |
| speed | 0–1          | 0 slow (100wpm) · 0.5 normal · 1 fast (250wpm) |

## Test

```bash
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"สวัสดีครับ","gender":"male","speed":0.5,"pitch":0.5}' \
  --output out.mp3
```
