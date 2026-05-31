"""28-day rotating curriculum — cycles until due date / birth."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

PT = ZoneInfo("America/Los_Angeles")


@dataclass(frozen=True)
class DayTopic:
    day_index: int  # 1-28 within cycle
    phase: str  # countdown | labor | birth | postpartum
    title: str
    focus: str
    partner_hook: str


# One focused theme per day. Repeats every 28 days if pregnancy runs long.
CURRICULUM: tuple[DayTopic, ...] = (
    DayTopic(1, "countdown", "Signs labor is starting", "Real labor vs practice contractions; when to call; when to stay home", "Your job: track timing, don't panic at every cramp"),
    DayTopic(2, "countdown", "When to go to the hospital", "4-1-1 rule, water broke, bleeding, reduced movement — hospital admit thresholds", "Ask your OB now what *their* admit threshold is"),
    DayTopic(3, "countdown", "The hospital bag", "What you actually use vs what lists overpack; charger, snacks, birth plan copies", "Pack duplicate copies of the birth plan — one for you, one for triage"),
    DayTopic(4, "countdown", "Avoiding unnecessary induction", "Expectant management, NST/BPP alternatives, evidence on postdates", "Magic phrase: evidence-based indication before starting labor artificially"),
    DayTopic(5, "countdown", "BRAIN for every offer", "Benefits, Risks, Alternatives, Intuition, Nothing/Not now", "You say BRAIN out loud so she doesn't have to while in pain"),
    DayTopic(6, "countdown", "Who's in the room", "Shift changes, residents vs attending, when to ask for the attending", "At every shift change: hand off birth plan + epidural plan"),
    DayTopic(7, "countdown", "Sleep before labor", "Early labor at home; rest beats early admit + intervention cascade", "If she's sleeping, you sleep — or at least eat"),
    DayTopic(8, "labor", "Stages of labor (quick map)", "Early → active → transition → pushing; what's normal at each", "Stage names help you ask smarter questions, not read the monitor"),
    DayTopic(9, "labor", "Epidural timing", "Active labor sweet spot; still push effectively; position changes after", "After epidural: position every 30-60 min — peanut ball, side-lying"),
    DayTopic(10, "labor", "Pitocin decisions", "Why offered, lowest dose, stronger contractions, failure-to-progress clocks", "Ask: is there a medical reason for mom or baby *right now*?"),
    DayTopic(11, "labor", "Breaking the water (AROM)", "No going back; hospital time limits; when waiting is valid", "Ask: does this start a clock for us?"),
    DayTopic(12, "labor", "The stall at 6-8 cm", "Very common with epidural; position, patience, not automatic C-section", "Before surgery for progress: what exactly hasn't progressed?"),
    DayTopic(13, "labor", "Fetal monitoring without panic", "Decelerations vs sustained bad patterns; ask if baby is OK *now*", "You don't read the strip — you ask: urgent or OK?"),
    DayTopic(14, "labor", "Pushing phase", "Coached vs spontaneous urge; ring of fire; swelling from pushing too early", "Can she push when she feels pressure, not on a count?"),
    DayTopic(15, "labor", "C-section conversations", "Distress vs failure to progress; resident vs attending; gentle C-section options", "Is baby in distress right now, or is this for progress?"),
    DayTopic(16, "labor", "Emergency moments", "Shoulder dystocia, cord prolapse, heavy bleeding — cooperate immediately", "Know the difference: debate progress, don't debate true emergency"),
    DayTopic(17, "birth", "First hour: skin-to-skin", "Delay non-urgent procedures; say it out loud to the team", "We'd like skin-to-skin immediately if baby is stable"),
    DayTopic(18, "birth", "Newborn procedures", "Vitamin K, eye ointment, Hep B — defaults vs your prefs", "Know your prefs *before* — you won't decide well exhausted"),
    DayTopic(19, "birth", "APGAR scores", "1-min vs 5-min; not an IQ test; ask is baby OK", "Low 1-min with normal 5-min is common"),
    DayTopic(20, "birth", "If baby goes to NICU/warmer", "Precaution vs emergency; hold first; pumped colostrum", "Can she hold baby first? Can I go with baby?"),
    DayTopic(21, "birth", "Breastfeeding day 1", "Cluster feeding, latch help, formula isn't failure", "Request lactation consultant early — don't wait until discharge"),
    DayTopic(22, "postpartum", "Her body: normal vs call now", "Bleeding, fever, headache+vision (postpartum preeclampsia), clots", "First 48 hours postpartum is still high-risk for *her*"),
    DayTopic(23, "postpartum", "Baby blues vs PPD", "Days 2-5 swings; when to escalate; partners get PPD too", "Severe mood crash or scary thoughts — call now, both of you"),
    DayTopic(24, "postpartum", "Sleep and visitors", "You are the gatekeeper; protect her sleep for two weeks minimum", "No is a complete sentence to visitors"),
    DayTopic(25, "postpartum", "Going home logistics", "Car seat check, pediatrician 2-3 days, who to call for what", "Write three numbers on the fridge: OB, pediatrician, L&D nurse line"),
    DayTopic(26, "postpartum", "Jaundice and baby fever", "Yellow skin common; rectal temp 100.4°F = emergency", "Pediatrician visit timing before discharge — know the rule"),
    DayTopic(27, "postpartum", "Partner survival", "You will be useless for a stretch; eat; don't take labor tone personally", "Adrenaline crash after birth is normal for you too"),
    DayTopic(28, "postpartum", "Advocacy doesn't end at birth", "Postpartum appointments, feeding struggles, mental health check-ins", "Schedule her 2-week and 6-week follow-ups before you leave the hospital if you can"),
)


def _parse_due_date(raw: str | None) -> date | None:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def days_until_due(due: date, *, today: date | None = None) -> int:
    today = today or datetime.now(tz=PT).date()
    return (due - today).days


def topic_for_today(*, due_date: str | None = None, anchor: date | None = None) -> DayTopic:
    """Pick today's topic from the 28-day cycle.

    If ``due_date`` is set and we're within 28 days before due, map day-by-day
    onto the curriculum (day -28 → topic 1, day 0 → topic 28). Otherwise rotate
    by calendar day since ``anchor`` (default: 2026-01-01).
    """
    today = datetime.now(tz=PT).date()
    due = _parse_due_date(due_date)

    if due is not None:
        d = days_until_due(due, today=today)
        if 0 <= d <= 27:
            # Countdown: 27 days out → topic 1, due date → topic 28
            idx = 28 - d
            return CURRICULUM[idx - 1]
        if d < 0:
            # Post-due: cycle postpartum-heavy topics
            return CURRICULUM[(-d - 1) % len(CURRICULUM)]

    anchor = anchor or date(2026, 1, 1)
    day_num = (today - anchor).days
    return CURRICULUM[day_num % len(CURRICULUM)]
