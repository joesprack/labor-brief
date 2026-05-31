#!/usr/bin/env python3
"""Labor & birth prep daily brief + mini podcast for Hermes cron delivery.

Each morning edition:
1. Picks today's topic from a 28-day curriculum (optionally aligned to due date)
2. Pulls pregnancy/birth RSS headlines + curated book/podcast/blog themes
3. LLM produces 1-3 focused, scannable cards with source excerpts
4. Generates a short TTS mini-podcast (Edge TTS)
5. Prints Discord markdown + MEDIA: zip attachment for #labor-prep
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import textwrap
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import feedparser
import httpx

from labor_brief.sources import RSS_FEEDS, curated_block, curated_for_phase
from labor_brief.topics import DayTopic, days_until_due, topic_for_today

REPO = Path(__file__).resolve().parents[1]
EPISODES = REPO / "episodes"
BRIEFINGS = REPO / "briefings"
PT = ZoneInfo("America/Los_Angeles")

GITHUB_USER = os.environ.get("LABOR_BRIEF_GITHUB_USER", "joesprack")
GITHUB_REPO = os.environ.get("LABOR_BRIEF_GITHUB_REPO", "labor-brief")


def github_episode_url(slug: str) -> str:
    return f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/blob/main/episodes/{slug}.mp3"


def listen_line(slug: str) -> str:
    url = github_episode_url(slug)
    return (
        f"🎧 **Mini podcast:** [{slug}.mp3]({url}) — or unzip **{slug}.zip** attached below"
    )


DEFAULT_API_BASE = os.environ.get("LABOR_BRIEF_API_BASE", "http://localhost:4646/v1")
DEFAULT_MODEL = os.environ.get("LABOR_BRIEF_MODEL", "auto")
DEFAULT_VOICE = os.environ.get("LABOR_BRIEF_TTS_VOICE", "en-US-JennyNeural")
DEFAULT_TTS_RATE = os.environ.get("LABOR_BRIEF_TTS_RATE", "-4%")
DEFAULT_TTS_PITCH = os.environ.get("LABOR_BRIEF_TTS_PITCH", "+0Hz")
SEGMENT_PAUSE_SECS = float(os.environ.get("LABOR_BRIEF_SEGMENT_PAUSE", "0.8"))
DUE_DATE = os.environ.get("LABOR_BRIEF_DUE_DATE", "").strip() or None


@dataclass
class Headline:
    source: str
    title: str
    url: str
    summary: str


@dataclass
class Card:
    title: str
    excerpt: str
    source_name: str
    source_type: str
    url: str
    partner_tip: str


def _log(msg: str) -> None:
    print(f"[labor-brief] {msg}", file=sys.stderr, flush=True)


def _today_slug() -> str:
    return datetime.now(tz=PT).strftime("%Y-%m-%d")


def _pretty_date() -> str:
    return datetime.now(tz=PT).strftime("%A, %B %d, %Y")


def fetch_headlines(limit_per_feed: int = 8) -> list[Headline]:
    items: list[Headline] = []
    for source, url in RSS_FEEDS:
        try:
            parsed = feedparser.parse(url)
        except Exception as exc:  # noqa: BLE001
            _log(f"RSS skip {source}: {exc}")
            continue
        if getattr(parsed, "bozo", False) and not parsed.entries:
            _log(f"RSS empty/broken {source}: {getattr(parsed, 'bozo_exception', 'unknown')}")
            continue
        for entry in parsed.entries[:limit_per_feed]:
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            summary = re.sub(r"\s+", " ", (entry.get("summary") or entry.get("description") or ""))
            summary = re.sub(r"<[^>]+>", "", summary).strip()[:350]
            if title and link:
                items.append(Headline(source=source, title=title, url=link, summary=summary))
    return items


def _headlines_block(headlines: list[Headline]) -> str:
    lines = []
    for i, h in enumerate(headlines[:40], 1):
        lines.append(f"{i}. [{h.source}] {h.title}\n   URL: {h.url}\n   {h.summary}")
    return "\n".join(lines)


def _llm_json(prompt: str) -> dict[str, Any]:
    api_key = os.environ.get(
        "LABOR_BRIEF_API_KEY",
        os.environ.get("CURSOR_PROXY_API_KEY", "not-needed"),
    )
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a birth-education editor for expectant partners. "
                    "Respond with valid JSON only — no markdown fences, no commentary. "
                    "Educational content only — not medical advice; encourage OB/hospital as authority. "
                    "Never invent URLs; use only URLs provided in the prompt."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.35,
    }
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(
            f"{DEFAULT_API_BASE.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    return json.loads(content)


def _due_context() -> str:
    if not DUE_DATE:
        return "Due date not configured — use general curriculum rotation."
    from labor_brief.topics import _parse_due_date

    due = _parse_due_date(DUE_DATE)
    if not due:
        return f"Due date env set but unparseable: {DUE_DATE!r}"
    d = days_until_due(due)
    if d > 0:
        return f"Due date {due.isoformat()} — {d} days remaining."
    if d == 0:
        return f"Due date is TODAY ({due.isoformat()})."
    return f"Due date was {due.isoformat()} — {abs(d)} days ago (postpartum focus OK)."


def build_briefing(topic: DayTopic, headlines: list[Headline]) -> dict[str, Any]:
    curated = curated_for_phase(topic.phase)
    prompt = textwrap.dedent(
        f"""
        Date: {_pretty_date()} (Pacific Time)
        Due context: {_due_context()}

        TODAY'S FOCUS
        Phase: {topic.phase}
        Title: {topic.title}
        What to cover: {topic.focus}
        Partner angle: {topic.partner_hook}

        Produce 1-3 **divisible cards** — each card is ONE focused idea someone can
        read in 30 seconds or hear in ~30-45 seconds. Mix source types when possible:
        at least one from news/blog RSS if relevant, plus book or podcast attribution.

        Return JSON:
        {{
          "cards": [
            {{
              "title": "Short card headline",
              "excerpt": "2-4 sentences — scannable, concrete, actionable. Paraphrase sources; no jargon walls.",
              "source_name": "Publication / book / podcast / author",
              "source_type": "news|blog|book|podcast|guide",
              "url": "https://... (must be from candidates below, or curated URL, or empty string)",
              "partner_tip": "One sentence — what the partner does with this info today"
            }}
          ],
          "story_segments": [
            "Intro: 'Labor Prep Daily for {_pretty_date()}.' One sentence introducing today's theme: {topic.title}.",
            "One spoken segment per card (same order). Each 35-55 words. Natural transitions.",
            "Outro: one sentence recap + remind this is education not medical advice."
          ],
          "podcast_script": "Full script — all story_segments joined.",
          "sources_used": ["list of source names actually cited"]
        }}

        Spoken-radio rules for story_segments:
        - Short sentences (max ~18 words). Spell out numbers.
        - No URLs, markdown, or bullet points in spoken parts.
        - Warm, calm partner-friendly tone — not alarmist.

        Curated themes (attribute honestly):
        {curated_block(curated)}

        Recent RSS candidates (prefer pregnancy/birth/parenting relevance to today's focus):
        {_headlines_block(headlines)}
        """
    ).strip()
    return _llm_json(prompt)


def cards_from_payload(payload: dict[str, Any]) -> list[Card]:
    out: list[Card] = []
    for raw in payload.get("cards") or []:
        title = str(raw.get("title") or "").strip()
        excerpt = str(raw.get("excerpt") or "").strip()
        source_name = str(raw.get("source_name") or "").strip()
        source_type = str(raw.get("source_type") or "guide").strip()
        url = str(raw.get("url") or "").strip()
        partner_tip = str(raw.get("partner_tip") or "").strip()
        if title and excerpt:
            out.append(
                Card(
                    title=title,
                    excerpt=excerpt,
                    source_name=source_name,
                    source_type=source_type,
                    url=url,
                    partner_tip=partner_tip,
                )
            )
    return out


def _phase_emoji(phase: str) -> str:
    return {
        "countdown": "📅",
        "labor": "🤰",
        "birth": "👶",
        "postpartum": "💙",
    }.get(phase, "📋")


def format_markdown(topic: DayTopic, cards: list[Card], *, slug: str) -> str:
    due_line = ""
    if DUE_DATE:
        due_line = f"\n_Due date configured: {DUE_DATE}_\n"

    lines = [
        listen_line(slug),
        "",
        f"# {_phase_emoji(topic.phase)} Labor Prep Daily | {_pretty_date()} (PT)",
        "",
        f"**Today's theme:** {topic.title}  ",
        f"_{topic.focus}_",
        due_line,
        "",
    ]
    for i, card in enumerate(cards, 1):
        src = card.source_name or "Guide"
        stype = card.source_type or "guide"
        lines.extend(
            [
                f"---",
                f"### {i}. {card.title}",
                "",
                card.excerpt,
                "",
                f"📚 **Source:** {src} ({stype})",
            ]
        )
        if card.url:
            lines.append(card.url)
        if card.partner_tip:
            lines.append(f"**Partner move:** {card.partner_tip}")
        lines.append("")

    lines.append("_Education only — your OB and hospital policies decide what's safe for you._")
    return "\n".join(lines).strip()


async def _synthesize_mp3(
    text: str,
    out_path: Path,
    *,
    voice: str,
    rate: str,
    pitch: str,
) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(str(out_path))


def _story_segments_from_payload(payload: dict[str, Any]) -> list[str]:
    raw_segments = payload.get("story_segments")
    if isinstance(raw_segments, list):
        segments = [re.sub(r"\s+", " ", str(s)).strip() for s in raw_segments]
        segments = [s for s in segments if s]
        if segments:
            return segments
    script = str(payload.get("podcast_script") or "").strip()
    if script:
        return [script]
    return []


def _ffmpeg_concat_mp3(segment_paths: list[Path], out_path: Path, pause_secs: float) -> None:
    if len(segment_paths) == 1:
        segment_paths[0].replace(out_path)
        return

    import tempfile

    with tempfile.TemporaryDirectory(prefix="labor-brief-tts-") as tmpdir:
        tmp = Path(tmpdir)
        silence_path = tmp / "pause.mp3"
        silence_cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=24000:cl=mono",
            "-t",
            str(pause_secs),
            "-q:a",
            "9",
            "-acodec",
            "libmp3lame",
            str(silence_path),
        ]
        subprocess.run(silence_cmd, check=True, capture_output=True, text=True)

        concat_list = tmp / "concat.txt"
        lines: list[str] = []
        for i, seg in enumerate(segment_paths):
            lines.append(f"file '{seg.as_posix()}'")
            if i < len(segment_paths) - 1:
                lines.append(f"file '{silence_path.as_posix()}'")
        concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")

        concat_cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            str(out_path),
        ]
        result = subprocess.run(concat_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {result.stderr or result.stdout}")


def synthesize_podcast(
    segments: list[str],
    out_path: Path,
    *,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_TTS_RATE,
    pitch: str = DEFAULT_TTS_PITCH,
    pause_secs: float = SEGMENT_PAUSE_SECS,
) -> None:
    import tempfile

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not segments:
        raise ValueError("No TTS segments to synthesize")

    with tempfile.TemporaryDirectory(prefix="labor-brief-seg-") as tmpdir:
        tmp = Path(tmpdir)
        segment_paths: list[Path] = []
        for i, segment in enumerate(segments):
            seg_path = tmp / f"seg-{i:02d}.mp3"
            asyncio.run(
                _synthesize_mp3(
                    segment,
                    seg_path,
                    voice=voice,
                    rate=rate,
                    pitch=pitch,
                )
            )
            segment_paths.append(seg_path)

        _ffmpeg_concat_mp3(segment_paths, out_path, pause_secs)

    _log(
        f"Wrote podcast {out_path} ({out_path.stat().st_size // 1024} KB, "
        f"{len(segments)} segments, voice={voice})"
    )


def _verify_episode_file(episode_path: Path) -> None:
    if not episode_path.is_file():
        raise RuntimeError(f"Episode file missing: {episode_path}")
    size = episode_path.stat().st_size
    if size < 1024:
        raise RuntimeError(f"Episode file too small ({size} bytes): {episode_path}")


def zip_episode(episode_path: Path, slug: str) -> Path:
    zip_path = EPISODES / f"{slug}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(episode_path, arcname=f"{slug}.mp3")
    _log(f"Wrote zip {zip_path} ({zip_path.stat().st_size // 1024} KB)")
    return zip_path


def publish_episode(episode_path: Path, slug: str) -> None:
    if not (REPO / ".git").is_dir():
        _log("No git repo — skipping publish")
        return

    rel = episode_path.relative_to(REPO)
    subprocess.run(["git", "add", str(rel)], cwd=REPO, check=True, capture_output=True, text=True)

    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True, check=True
    )
    if not status.stdout.strip():
        _log("Episode unchanged — skipping git commit")
    else:
        msg = f"Add Labor Prep episode {slug}"
        subprocess.run(["git", "commit", "-m", msg], cwd=REPO, check=True, capture_output=True, text=True)
        push = subprocess.run(["git", "push"], cwd=REPO, capture_output=True, text=True)
        if push.returncode != 0:
            raise RuntimeError(f"git push failed: {push.stderr or push.stdout}")
        _log(f"Archived episode to {GITHUB_USER}/{GITHUB_REPO}")


def save_briefing(topic: DayTopic, markdown: str, payload: dict[str, Any]) -> None:
    BRIEFINGS.mkdir(parents=True, exist_ok=True)
    slug = _today_slug()
    (BRIEFINGS / f"{slug}.md").write_text(markdown, encoding="utf-8")
    meta = {"topic": topic.title, "phase": topic.phase, **payload}
    (BRIEFINGS / f"{slug}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def run(*, dry_run: bool = False, skip_publish: bool = False) -> int:
    topic = topic_for_today(due_date=DUE_DATE)
    _log(f"Topic: {topic.title} ({topic.phase})")

    headlines = fetch_headlines()
    _log(f"Fetched {len(headlines)} RSS candidates")

    payload = build_briefing(topic, headlines)
    cards = cards_from_payload(payload)
    if not cards:
        print("⚠️ Labor Prep: LLM returned no cards — skipping delivery.", file=sys.stderr)
        return 1

    segments = _story_segments_from_payload(payload)
    if not segments:
        print("⚠️ Labor Prep: missing podcast segments — skipping delivery.", file=sys.stderr)
        return 1

    if not str(payload.get("podcast_script") or "").strip():
        payload["podcast_script"] = " ".join(segments)

    slug = _today_slug()
    episode_path = EPISODES / f"{slug}.mp3"

    if not dry_run:
        synthesize_podcast(segments, episode_path)
        _verify_episode_file(episode_path)
        if not skip_publish:
            publish_episode(episode_path, slug)

    markdown = format_markdown(topic, cards, slug=slug)

    if not dry_run:
        save_briefing(topic, markdown, payload)

    print(markdown)
    if not dry_run and episode_path.is_file():
        zip_path = zip_episode(episode_path, slug)
        print("[[as_document]]")
        print(f"MEDIA:{zip_path.resolve()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Skip TTS; print markdown only")
    parser.add_argument("--skip-publish", action="store_true", help="Generate MP3 without git push")
    args = parser.parse_args()
    return run(dry_run=args.dry_run, skip_publish=args.skip_publish)


if __name__ == "__main__":
    sys.exit(main())
