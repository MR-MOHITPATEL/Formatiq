"""
CSV export for all videos, analysis scores, and recommendation summaries.
"""
import io
import csv
from sqlalchemy.orm import Session

from database import Video, VideoAnalysis, FormatPoint


def export_all_videos_csv(db: Session) -> bytes:
    """Export all videos with metadata and all 24 format point scores."""
    format_points = db.query(FormatPoint).order_by(FormatPoint.number).all()
    fp_headers = [f"fp_{fp.number}_{fp.name[:20].replace(' ', '_')}" for fp in format_points]
    fp_flag_headers = [f"fp_{fp.number}_flag" for fp in format_points]

    videos = db.query(Video).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    base_headers = [
        "video_id", "title", "channel_name", "view_count", "like_count",
        "comment_count", "published_at", "duration_seconds", "format_point",
        "transcript_available", "analysis_status",
        "concept_summary", "health_niche_angle",
        "what_works", "what_doesnt_work",
    ]
    writer.writerow(base_headers + fp_headers + fp_flag_headers)

    for v in videos:
        an: VideoAnalysis | None = v.analysis
        scores = an.format_point_scores if an else {}
        flags = an.format_point_flags if an else {}

        fp_score_vals = [scores.get(fp.number, 0) for fp in format_points]
        fp_flag_vals = [1 if flags.get(fp.number, False) else 0 for fp in format_points]

        row = [
            v.video_id,
            v.title,
            v.channel_name,
            v.view_count,
            v.like_count,
            v.comment_count,
            v.published_at.isoformat() if v.published_at else "",
            v.duration_seconds,
            v.format_point.name if v.format_point else "",
            v.transcript_available,
            v.analysis_status,
            an.concept_summary if an else "",
            an.health_niche_angle if an else "",
            "; ".join(an.what_works or []) if an else "",
            "; ".join(an.what_doesnt_work or []) if an else "",
        ]
        writer.writerow(row + fp_score_vals + fp_flag_vals)

    return output.getvalue().encode("utf-8")


def export_format_point_csv(db: Session, format_point_id: int) -> bytes:
    """Export videos for a specific format point."""
    videos = db.query(Video).filter_by(format_point_id=format_point_id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "video_id", "title", "channel_name", "view_count", "like_count",
        "published_at", "analysis_status", "concept_summary", "health_niche_angle",
        "top_format_score", "what_works",
    ])

    for v in videos:
        an = v.analysis
        top_score = max((an.format_point_scores or {}).values(), default=0) if an else 0
        writer.writerow([
            v.video_id, v.title, v.channel_name, v.view_count, v.like_count,
            v.published_at.isoformat() if v.published_at else "",
            v.analysis_status,
            an.concept_summary if an else "",
            an.health_niche_angle if an else "",
            top_score,
            "; ".join((an.what_works or []) if an else []),
        ])

    return output.getvalue().encode("utf-8")
