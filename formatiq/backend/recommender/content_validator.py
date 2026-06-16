"""
Two-tier content validation: checks if a topic/angle performs well for
direct competitors AND the broader market before script generation.
"""
import logging
import statistics
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from database import Video, VideoAnalysis, Channel

logger = logging.getLogger(__name__)

MIN_FORMAT_SCORE = 6.0      # out of 10 — threshold for "format is used well"
MIN_RELATIVE_VIEWS = 0.8    # must reach 80% of the tier's median view count


def _get_tier_videos(db: Session, tier: str) -> list:
    """Return scraped videos from the past 12 months from channels in a given tier.
    Only fetches columns needed for keyword matching — skips transcript/thumbnail/etc."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    rows = (
        db.query(
            Video.video_id,
            Video.title,
            Video.description,
            Video.view_count,
            Video.channel_name,
        )
        .join(Channel, Video.channel_id == Channel.id)
        .filter(Channel.competitor_tier == tier)
        .filter(Video.published_at >= cutoff)
        .all()
    )
    return rows


def _score_topic_fit(videos: list[Video], topic: str) -> tuple[float, list[dict]]:
    """
    Score how well a topic performs in a set of videos.
    Returns (score 0-1, evidence list).
    score = fraction of videos whose title/transcript contains the topic keywords,
            weighted by relative view performance.
    """
    if not videos:
        return 0.0, []

    # Use only meaningful words (length > 3, skip stop words)
    stop_words = {"this", "that", "with", "from", "have", "been", "will", "your", "their", "what", "which", "about", "more", "also", "just", "after", "other", "into", "than", "them", "then", "some", "such", "when", "each", "most"}
    sig_words = [w for w in topic.lower().split() if len(w) > 3 and w not in stop_words]
    if not sig_words:
        return 0.0, []

    all_views = [v.view_count or 0 for v in videos]
    median_views = statistics.median(all_views) if all_views else 1

    # Require at least 2 significant keyword matches (or all if fewer than 2 exist)
    min_matches = min(2, len(sig_words))

    matching = []
    for v in videos:
        text = f"{v.title or ''} {v.description or ''}".lower()
        hit_count = sum(1 for w in sig_words if w in text)
        if hit_count >= min_matches:
            rel_views = (v.view_count or 0) / max(median_views, 1)
            matching.append({
                "video_id": v.video_id,
                "title": v.title,
                "view_count": v.view_count,
                "channel_name": v.channel_name,
                "relative_views": round(rel_views, 2),
                "youtube_url": f"https://www.youtube.com/watch?v={v.video_id}",
            })

    if not matching:
        return 0.0, []

    # Score = fraction of matching videos above the relative-view threshold
    above_threshold = [m for m in matching if m["relative_views"] >= MIN_RELATIVE_VIEWS]
    score = len(above_threshold) / max(len(matching), 1)

    # Return top evidence videos sorted by view count
    evidence = sorted(matching, key=lambda x: x["view_count"] or 0, reverse=True)[:5]
    return score, evidence


def validate_content_angle(db: Session, topic: str, angle: str = "") -> dict:
    """
    Run two-tier validation for a topic/angle.

    Returns:
      {
        direct_validated: bool,
        market_validated: bool,
        go: bool,
        direct_score: float,
        market_score: float,
        direct_evidence: [...],
        market_evidence: [...],
        direct_video_count: int,
        market_video_count: int,
        message: str,
      }
    """
    search_text = f"{topic} {angle}".strip()

    direct_videos = _get_tier_videos(db, "direct")
    market_videos = _get_tier_videos(db, "market")

    direct_score, direct_evidence = _score_topic_fit(direct_videos, search_text)
    market_score, market_evidence = _score_topic_fit(market_videos, search_text)

    # If a tier has no channels configured, treat it as passing (don't block the user)
    direct_validated = direct_score >= 0.3 if direct_videos else True
    market_validated = market_score >= 0.3 if market_videos else True

    go = direct_validated and market_validated

    if not direct_videos and not market_videos:
        message = "No competitor data found. Scrape competitor channels first for accurate validation."
    elif go:
        message = f"Content angle validated ✓ — performing in both direct competitors and broader market."
    elif not direct_validated and not market_validated:
        message = "This angle underperforms in both your direct competitors and the broader market."
    elif not direct_validated:
        message = "This angle underperforms for your direct competitors, but shows potential in the broader market."
    else:
        message = "Direct competitors use this angle well, but it has limited presence in the broader market."

    return {
        "direct_validated": direct_validated,
        "market_validated": market_validated,
        "go": go,
        "direct_score": round(direct_score, 2),
        "market_score": round(market_score, 2),
        "direct_evidence": direct_evidence,
        "market_evidence": market_evidence,
        "direct_video_count": len(direct_videos),
        "market_video_count": len(market_videos),
        "message": message,
    }
