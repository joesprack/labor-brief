# Labor Prep Daily

Morning birth-education brief for Discord `#labor-prep` — focused cards with source excerpts (news, blogs, books, podcasts) plus a mini podcast.

Each edition:

1. Picks today's theme from a **28-day curriculum** (countdown → labor → birth → postpartum)
2. Pulls relevant RSS headlines + curated book/podcast/blog themes
3. LLM produces **1–3 scannable cards** (divisible, one idea each)
4. Generates a **~2–4 minute mini podcast** with Edge TTS (`en-US-JennyNeural`)
5. Delivers to `#labor-prep`: markdown brief + zip MP3 via Hermes `MEDIA:`

## Setup

```bash
cd ~/git/labor-brief
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Optional in `~/.hermes/.env`:

```bash
LABOR_BRIEF_DUE_DATE=2026-07-15        # YYYY-MM-DD — aligns curriculum to countdown
LABOR_BRIEF_TTS_VOICE=en-US-JennyNeural
LABOR_BRIEF_TTS_RATE=-4%
```

Hermes cron: `~/.hermes/scripts/labor_brief_morning.sh` at **7:30 AM PT** daily.

## Manual test

```bash
.venv/bin/python -m labor_brief.run --dry-run
.venv/bin/python -m labor_brief.run --skip-publish
```

## Education disclaimer

Content is for partner education and advocacy prep — not medical advice. OB and hospital policies always win.
