"""
Competitor gap analysis — finds under/over-used format points.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import Video, VideoAnalysis, FormatPoint, Channel


def compute_gap_analysis(db: Session) -> list[dict]:
    """
    For each format point, calculate:
    - avg_score: average score across all analyzed videos
    - total_videos: how many videos use this format point
    - avg_views_when_used: average views when this format is actively used
    - competitor_saturation: % of competitor channels using this format
    - opportunity_score: inverse of saturation × performance
    """
    format_points = db.query(FormatPoint).order_by(FormatPoint.number).all()
    analyses = db.query(VideoAnalysis).join(Video).all()

    if not analyses:
        return []

    # Per format point stats
    results = []
    total_channels = db.query(func.count(Channel.id.distinct())).scalar() or 1

    for fp in format_points:
        fp_scores = []
        fp_views_used = []
        fp_channel_ids = set()

        for an in analyses:
            score = (an.format_point_scores or {}).get(fp.number, 0)
            flag = (an.format_point_flags or {}).get(fp.number, False)

            fp_scores.append(score)

            if flag and an.video:
                fp_views_used.append(an.video.view_count or 0)
                if an.video.channel:
                    fp_channel_ids.add(an.video.channel_id)

        avg_score = sum(fp_scores) / len(fp_scores) if fp_scores else 0
        avg_views = sum(fp_views_used) / len(fp_views_used) if fp_views_used else 0
        saturation = len(fp_channel_ids) / total_channels

        # Opportunity = high performance + low saturation
        opportunity_score = avg_views * (1 - saturation * 0.5)

        results.append({
            "format_point_id": fp.id,
            "format_point_number": fp.number,
            "format_point_name": fp.name,
            "avg_score": round(avg_score, 2),
            "videos_using": len(fp_views_used),
            "avg_views_when_used": round(avg_views),
            "competitor_saturation_pct": round(saturation * 100, 1),
            "opportunity_score": round(opportunity_score),
            "status": _classify(saturation, avg_views),
        })

    results.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return results


def _classify(saturation: float, avg_views: float) -> str:
    if saturation < 0.3 and avg_views > 50000:
        return "HIGH_OPPORTUNITY"
    elif saturation < 0.3:
        return "UNDERUSED"
    elif saturation > 0.7 and avg_views < 50000:
        return "SATURATED_LOW_PERFORMANCE"
    elif saturation > 0.7:
        return "SATURATED_HIGH_PERFORMANCE"
    else:
        return "MODERATE"
