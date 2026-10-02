"""Synthetic segment log generator.

Builds 320 synthetic segments (160 per quarter) for a fictional weekly,
hour-long public-affairs show across 2 real calendar quarters: Q4 2025
(Oct-Dec) and Q1 2026 (Jan-Mar). Every segment, narrative, date and
duration here is invented for this project; no real station, show or
broadcast is behind any of it.

Non-uniform by design: each of the 8 categories gets a different, fixed
segment count per quarter (27 down to 13, strictly decreasing) so the
least-airtime ranking has a real, non-tied answer to measure rather than
an assumed one. Durations are drawn from a per-category range with a
seeded PRNG, so two categories with close counts cannot silently tie on
total minutes by construction alone; `rank_categories` is still the
thing that decides the order, from measured totals, not from this
module's intent.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from qipc.categories import CATEGORIES
from qipc.deadlines import Quarter

SEED = 20260401  # fixed, so every run of the pipeline reproduces the same 320 segments

# Segment count per category, per quarter. Strictly decreasing so no two
# categories start from the same count; sums to 160.
_CATEGORY_SEGMENT_COUNTS = {
    "Education": 27,
    "Housing": 25,
    "Public Safety": 23,
    "Health": 21,
    "Environment": 19,
    "Transportation": 17,
    "Economic Development": 15,
    "Civic Engagement": 13,
}
assert sum(_CATEGORY_SEGMENT_COUNTS.values()) == 160
assert set(_CATEGORY_SEGMENT_COUNTS) == set(CATEGORIES)

# Per-category duration range in minutes. A segment is a magazine-style
# piece within an hour-long weekly show, not a full episode.
_CATEGORY_DURATION_RANGE_MIN = {
    "Education": (3, 7),
    "Housing": (3, 7),
    "Public Safety": (3, 6),
    "Health": (3, 6),
    "Environment": (2, 6),
    "Transportation": (2, 5),
    "Economic Development": (2, 5),
    "Civic Engagement": (2, 5),
}

_AIR_TIME = "19:00"  # fixed 7pm slot for every episode of the weekly show

_NARRATIVE_TEMPLATES = {
    "Education": [
        "School board budget vote and its effect on {neighborhood} elementary enrollment.",
        "Tutoring shortage follow-up: district response and new volunteer sign-ups.",
        "Local college tuition-assistance program for first-generation students.",
        "Teacher vacancy rates at {neighborhood} schools compared to last year.",
        "Panel of parents on the district's new reading curriculum.",
    ],
    "Housing": [
        "Affordable housing waitlist times at the {neighborhood} development.",
        "Tenant rights clinic turnout and the eviction filings it addressed.",
        "City council vote on the rezoning proposal near {neighborhood}.",
        "First-time homebuyer assistance fund, one year after launch.",
        "Rising rents in {neighborhood} and what the city's data shows.",
    ],
    "Public Safety": [
        "Neighborhood watch expansion in {neighborhood} after a rise in reported incidents.",
        "Fire department response-time audit for the {neighborhood} station.",
        "New crosswalk signals installed after resident petition in {neighborhood}.",
        "Police department community-liaison program, six months in.",
        "Emergency preparedness drill results for the {neighborhood} district.",
    ],
    "Health": [
        "Mobile vaccination clinic visits {neighborhood} this month.",
        "Hospital emergency-room wait times, a follow-up investigation.",
        "Mental health hotline call volume and funding renewal debate.",
        "Community health fair turnout in {neighborhood}.",
        "Access to primary care in {neighborhood}, a data-driven look.",
    ],
    "Environment": [
        "Storm drain upgrade project near {neighborhood} and flood risk reduction.",
        "Recycling participation rates across the city's districts.",
        "Tree-planting initiative progress in {neighborhood}.",
        "Air quality monitoring station results for {neighborhood}.",
        "Community garden expansion and its effect on local produce access.",
    ],
    "Transportation": [
        "Bus route changes affecting {neighborhood} commuters.",
        "Pothole repair backlog update for {neighborhood} streets.",
        "New bike lane safety data six months after installation.",
        "Transit fare assistance program enrollment numbers.",
        "Road construction delays near the {neighborhood} interchange.",
    ],
    "Economic Development": [
        "Small business grant recipients in {neighborhood}, one year later.",
        "New employer announcement and projected {neighborhood} hiring.",
        "Downtown vacancy rate trends compared to pre-pandemic levels.",
        "Workforce training program graduation numbers this quarter.",
        "Chamber of commerce survey on {neighborhood} retail recovery.",
    ],
    "Civic Engagement": [
        "Voter registration drive turnout ahead of the local election.",
        "Town hall attendance on the proposed {neighborhood} budget.",
        "New resident advisory board seats and who applied.",
        "Civics program for high schoolers launches in {neighborhood}.",
        "Public comment period results on the city's strategic plan.",
    ],
}

_NEIGHBORHOODS = [
    "Elm Heights", "Rosedale", "Harbor Point", "Fenwick Park",
    "Garfield Crossing", "Northgate", "Maple Ridge", "Union Flats",
]


def _sundays_in_quarter(q: Quarter) -> list[date]:
    """Every Sunday (the show's weekly air day) whose date falls inside the quarter."""
    d = q.start_date
    d += timedelta(days=(6 - d.weekday()) % 7)  # weekday(): Mon=0..Sun=6
    out = []
    while d <= q.end_date:
        out.append(d)
        d += timedelta(days=7)
    return out


def _episode_assignment(rng: random.Random, n_segments: int, n_episodes: int) -> list[int]:
    """Assign each of n_segments a 0-indexed episode number, spread evenly."""
    base = n_segments // n_episodes
    remainder = n_segments % n_episodes
    counts = [base] * n_episodes
    extra_episodes = rng.sample(range(n_episodes), remainder)
    for e in extra_episodes:
        counts[e] += 1
    episode_for_segment = []
    for ep_idx, cnt in enumerate(counts):
        episode_for_segment.extend([ep_idx] * cnt)
    rng.shuffle(episode_for_segment)
    return episode_for_segment


def generate_quarter_segments(q: Quarter, rng: random.Random) -> list[dict]:
    sundays = _sundays_in_quarter(q)
    n_episodes = len(sundays)

    rows: list[dict] = []
    for category in CATEGORIES:
        count = _CATEGORY_SEGMENT_COUNTS[category]
        lo, hi = _CATEGORY_DURATION_RANGE_MIN[category]
        episode_for = _episode_assignment(rng, count, n_episodes)
        templates = _NARRATIVE_TEMPLATES[category]
        for i in range(count):
            ep_idx = episode_for[i]
            air_date = sundays[ep_idx]
            duration = rng.randint(lo, hi)
            template = rng.choice(templates)
            narrative = template.format(neighborhood=rng.choice(_NEIGHBORHOODS))
            rows.append(
                {
                    "air_date": air_date.isoformat(),
                    "air_time": _AIR_TIME,
                    "duration_min": duration,
                    "category": category,
                    "narrative": narrative,
                    "quarter_year": q.year,
                    "quarter_number": q.quarter,
                    "episode_index": ep_idx,
                }
            )
    return rows


def generate_all_segments(quarters: list[Quarter], seed: int = SEED) -> list[dict]:
    """Generate the full synthetic log for the given quarters, deterministically."""
    rng = random.Random(seed)
    rows: list[dict] = []
    for q in quarters:
        rows.extend(generate_quarter_segments(q, rng))
    return rows


DEFAULT_QUARTERS = [Quarter(2025, 4), Quarter(2026, 1)]
