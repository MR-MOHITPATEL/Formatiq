"""
Angle Intelligence: analyzes own-channel video angle performance
and recommends the best angle combination for the next script.
Scores by view count (falls back to Gemini strength score if views unavailable).
Supports topic-specific filtering.
"""
import logging
from itertools import combinations
from sqlalchemy.orm import Session
from database import Video, Channel, VideoAngleAnalysis, GeneratedScript

logger = logging.getLogger(__name__)

ANGLES = ["villain", "hero", "credibility", "virality", "moral_ground"]
ANGLE_LABELS = {
    "villain":      "Villain (Real Culprit)",
    "hero":         "Hero (Solution)",
    "credibility":  "Credibility (Research/Data)",
    "virality":     "Virality (Surprising Fact)",
    "moral_ground": "Moral Ground (Viewer Protection)",
}

_KW_STOP = {
    "this", "that", "with", "from", "have", "been", "will", "your", "their",
    "what", "which", "about", "also", "just", "after", "other", "into", "high",
    "best", "good", "only", "most", "more", "less", "very", "does", "gets",
}


def _get_own_angle_analyses(db: Session) -> list[dict]:
    """Fetch 5-angle analyses for own-channel videos, including view count."""
    rows = (
        db.query(VideoAngleAnalysis, Video)
        .join(Video, VideoAngleAnalysis.video_id == Video.id)
        .join(Channel, Video.channel_id == Channel.id)
        .filter(Channel.competitor_tier == "own")
        .all()
    )
    results = []
    for analysis, video in rows:
        results.append({
            "video_id": video.video_id,
            "title": video.title or "",
            "view_count": video.view_count or 0,
            "strength": analysis.overall_strength or 5,
            "angles": {
                "villain":      analysis.villain_present,
                "hero":         analysis.hero_present,
                "credibility":  analysis.credibility_present,
                "virality":     analysis.virality_present,
                "moral_ground": analysis.moral_ground_present,
            },
        })
    return results


def _filter_by_topic(analyses: list[dict], topic: str) -> tuple[list[dict], bool]:
    """
    Filter analyses to videos related to the given topic.
    Returns (filtered_list, is_topic_filtered).
    Falls back to all videos if fewer than 3 related videos found.
    """
    if not topic or len(topic.strip()) < 3:
        return analyses, False

    keywords = [
        w for w in topic.lower().split()
        if len(w) > 3 and w not in _KW_STOP
    ]
    if not keywords:
        return analyses, False

    related = [
        v for v in analyses
        if any(kw in v["title"].lower() for kw in keywords)
    ]

    if len(related) >= 3:
        return related, True
    # Not enough topic-specific videos — return all with a flag
    return analyses, False


def _score_angles(analyses: list[dict]) -> dict[str, float]:
    """
    Score each angle 0-25 weighted by view count.
    Falls back to overall_strength × 10000 if view count is 0.
    Scores are NOT normalized to max=25 — they reflect actual weighted frequency.
    """
    if not analyses:
        return {a: 0.0 for a in ANGLES}

    has_views = any(v["view_count"] > 0 for v in analyses)

    angle_weighted_sum = {a: 0.0 for a in ANGLES}
    angle_total_possible = {a: 0.0 for a in ANGLES}

    for v in analyses:
        # Weight = view count if available, else strength-based estimate
        weight = v["view_count"] if has_views and v["view_count"] > 0 else v["strength"] * 10000

        for angle in ANGLES:
            angle_total_possible[angle] += weight
            if v["angles"].get(angle):
                angle_weighted_sum[angle] += weight

    # Score = (weighted views where angle present) / (total weighted views) × 25
    scores = {}
    for a in ANGLES:
        total = angle_total_possible[a]
        if total > 0:
            scores[a] = round((angle_weighted_sum[a] / total) * 25, 1)
        else:
            scores[a] = 0.0

    return scores


def _best_combo(analyses: list[dict], scores: dict[str, float]) -> list[str]:
    """
    Find the 2-angle combo that appears together in the highest-viewed videos.
    Uses view-count weighted co-occurrence.
    """
    has_views = any(v["view_count"] > 0 for v in analyses)

    combo_scores: dict[tuple, float] = {}
    for pair in combinations(ANGLES, 2):
        total = 0.0
        for v in analyses:
            if all(v["angles"].get(a) for a in pair):
                weight = v["view_count"] if has_views and v["view_count"] > 0 else v["strength"] * 10000
                total += weight
        if total > 0:
            combo_scores[pair] = total

    if not combo_scores:
        # Fall back to top-2 by score
        return sorted(scores, key=lambda a: scores[a], reverse=True)[:2]

    best_pair = max(combo_scores, key=lambda p: combo_scores[p])
    return list(best_pair)


def _get_recent_script_combos(db: Session, n: int = 3) -> list[str]:
    """Return angle strings from the last N generated scripts."""
    rows = (
        db.query(GeneratedScript)
        .order_by(GeneratedScript.created_at.desc())
        .limit(n)
        .all()
    )
    return [row.angle for row in rows if row.angle]


def _build_gemini_insight(
    gemini_analyzer,
    scores: dict[str, float],
    best_combo: list[str],
    recent_combos: list[str],
    video_count: int,
    topic: str = "",
    is_topic_filtered: bool = False,
) -> str:
    """Use Gemini Flash to generate a 2-sentence actionable insight."""
    score_lines = "\n".join(
        f"- {ANGLE_LABELS[a]}: {scores[a]}/25 pts" for a in ANGLES
    )
    recent_str = ", ".join(recent_combos[-3:]) if recent_combos else "None yet"
    best_str = " + ".join(ANGLE_LABELS[a] for a in best_combo)
    scope = f"for '{topic}' videos specifically" if is_topic_filtered else "across all videos"
    has_views = any(scores[a] > 0 for a in ANGLES)
    basis = "view count data" if has_views else "content quality scores"

    prompt = f"""You are an AI advisor for a doctor's YouTube channel.
Based on analysis of {video_count} videos ({scope}), using {basis}:

{score_lines}

Best performing combination: {best_str}
Recent script angles used: {recent_str}

Write exactly 2 short sentences recommending what angle combination to use next.
- Be specific and actionable
- If recent scripts repeated the same combo, suggest a change
- Do NOT use the words: villain, hero, virality, moral ground
- Plain language a doctor would understand
- Under 50 words total

Return ONLY the 2 sentences. No labels, no JSON."""

    try:
        from google import genai
        client = genai.Client(api_key=gemini_analyzer.api_key)
        response = client.models.generate_content(
            model=gemini_analyzer.model,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        logger.warning(f"Gemini insight generation failed: {e}")
        return f"Your strongest combination is {best_str} based on {video_count} videos. Use this in your next script for maximum impact."


def get_angle_performance(db: Session, gemini_analyzer=None, topic: str = "") -> dict:
    """
    Main function: compute angle scores, best combo, and AI insight.
    If topic is provided, scores are filtered to topic-relevant videos.
    """
    all_analyses = _get_own_angle_analyses(db)

    if not all_analyses:
        return {
            "has_data": False,
            "video_count": 0,
            "filtered_video_count": 0,
            "is_topic_filtered": False,
            "scores": {a: 0.0 for a in ANGLES},
            "best_combo": [],
            "best_combo_labels": [],
            "insight": "No own-channel videos analyzed yet. Go to Controls → click 'Analyze All Videos (5-Angle)'.",
            "angle_labels": ANGLE_LABELS,
        }

    analyses, is_topic_filtered = _filter_by_topic(all_analyses, topic)
    has_views = any(v["view_count"] > 0 for v in analyses)

    scores = _score_angles(analyses)
    best_combo = _best_combo(analyses, scores)
    recent_combos = _get_recent_script_combos(db, n=3)

    insight = _build_gemini_insight(
        gemini_analyzer, scores, best_combo, recent_combos,
        len(analyses), topic=topic, is_topic_filtered=is_topic_filtered,
    ) if gemini_analyzer else (
        f"Your strongest combination is {' + '.join(ANGLE_LABELS[a] for a in best_combo)} "
        f"based on {len(analyses)} videos."
    )

    return {
        "has_data": True,
        "video_count": len(all_analyses),
        "filtered_video_count": len(analyses),
        "is_topic_filtered": is_topic_filtered,
        "score_basis": "view_count" if has_views else "quality_score",
        "scores": scores,
        "best_combo": best_combo,
        "best_combo_labels": [ANGLE_LABELS[a] for a in best_combo],
        "insight": insight,
        "angle_labels": ANGLE_LABELS,
        "recent_combos": recent_combos,
    }
