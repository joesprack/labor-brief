"""RSS feeds and curated source excerpts for labor-brief."""

from __future__ import annotations

from dataclasses import dataclass

# Pregnancy / birth / parenting RSS (public, no paywall scraping)
RSS_FEEDS: list[tuple[str, str]] = [
    ("Evidence Based Birth", "https://evidencebasedbirth.com/feed/"),
    ("NPR Health", "https://feeds.npr.org/1128/rss.xml"),
    ("What to Expect", "https://www.whattoexpect.com/news/rss.xml"),
    ("BabyCenter News", "https://www.babycenter.com/feeds/news.rss"),
    ("Parents.com", "https://www.parents.com/feeds/rss/news.xml"),
]

# Curated paraphrased themes with attribution — LLM expands into cards, not verbatim quotes.
@dataclass(frozen=True)
class CuratedSource:
    title: str
    source_type: str  # book | podcast | blog | guide
    author: str
    url: str
    themes: tuple[str, ...]
    phase_tags: tuple[str, ...]


CURATED: tuple[CuratedSource, ...] = (
    CuratedSource(
        "The Birth Partner",
        "book",
        "Penny Simkin",
        "https://www.pennysimkin.com/",
        (
            "Labor support is about rhythm, comfort, and advocacy — not fixing pain.",
            "Use the five-question framework before any intervention.",
            "Position changes and movement often unlock stalls better than more Pitocin.",
        ),
        ("labor", "countdown"),
    ),
    CuratedSource(
        "Expecting Better",
        "book",
        "Emily Oster",
        "https://expectingbetter.com/",
        (
            "Induction for convenience vs medical indication — know the evidence for your situation.",
            "Ultrasound weight estimates have wide error bars; 'big baby' alone is a weak reason to induce.",
        ),
        ("countdown",),
    ),
    CuratedSource(
        "Evidence Based Birth",
        "blog",
        "Rebecca Dekker, PhD, RN",
        "https://evidencebasedbirth.com/",
        (
            "Continuous fetal monitoring increases intervention rates without improving outcomes for low-risk births.",
            "Delayed cord clamping benefits most term babies when baby is stable.",
            "Peanut ball and side-lying positions help progress with epidural.",
        ),
        ("labor", "birth"),
    ),
    CuratedSource(
        "Birthful",
        "podcast",
        "Maya Litz",
        "https://birthful.com/",
        (
            "Partners who know one comfort technique cold — hip squeeze, counter-pressure — matter more than knowing everything.",
            "Early labor is often boring; boredom at the hospital leads to unnecessary interventions.",
        ),
        ("countdown", "labor"),
    ),
    CuratedSource(
        "The Fourth Trimester",
        "book",
        "Kimberly Ann Johnson",
        "https://kimberlyannjohnson.com/",
        (
            "Postpartum recovery is a physical injury timeline — rest is medical, not lazy.",
            "Pelvic floor and core healing take weeks; rushing activity increases long-term problems.",
        ),
        ("postpartum",),
    ),
    CuratedSource(
        "Happiest Baby on the Block",
        "book",
        "Harvey Karp, MD",
        "https://www.happiestbaby.com/",
        (
            "The 5 S's — swaddle, side/stomach position for soothing, shush, swing, suck — for the fourth trimester fussies.",
            "Cluster feeding at night is normal; protect mom's sleep where you can.",
        ),
        ("birth", "postpartum"),
    ),
    CuratedSource(
        "Mindful Birthing",
        "book",
        "Nancy Bardacke",
        "https://www.mindfulbirthing.org/",
        (
            "Pain vs suffering — pain is sensation; suffering is fighting the sensation.",
            "Breath and grounding help between contractions; partner mirrors calm breathing.",
        ),
        ("labor", "countdown"),
    ),
    CuratedSource(
        "NPR Life Kit: Birth",
        "podcast",
        "NPR",
        "https://www.npr.org/lifekit",
        (
            "Write a one-page birth preferences doc, not a rigid script — flexibility when medically necessary.",
            "Ask who will actually be delivering — resident, midwife, or attending.",
        ),
        ("countdown", "labor"),
    ),
)


def curated_for_phase(phase: str, limit: int = 6) -> list[CuratedSource]:
    out: list[CuratedSource] = []
    for src in CURATED:
        if phase in src.phase_tags or not src.phase_tags:
            out.append(src)
        if len(out) >= limit:
            break
    return out or list(CURATED[:limit])


def curated_block(sources: list[CuratedSource]) -> str:
    lines: list[str] = []
    for s in sources:
        lines.append(f"- [{s.source_type}] {s.title} by {s.author} ({s.url})")
        for theme in s.themes:
            lines.append(f"    • {theme}")
    return "\n".join(lines)
