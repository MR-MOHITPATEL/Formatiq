"""
Recommendation engine — generates format point reports and next-video ideas.
"""
import json
import logging
from collections import Counter
from sqlalchemy.orm import Session

from database import Video, VideoAnalysis, FormatPoint, Recommendation
from analyzer.claude_analyzer import ClaudeAnalyzer
from analyzer.prompts import build_format_point_report_prompt, build_next_video_prompt

logger = logging.getLogger(__name__)


def get_format_point_report(
    db: Session,
    analyzer: ClaudeAnalyzer,
    format_point_id: int,
    regenerate: bool = False,
) -> dict:
    """Generate (or retrieve cached) report for a single format point."""
    fp = db.query(FormatPoint).filter_by(id=format_point_id).first()
    if not fp:
        return {}

    # Check cache
    if not regenerate:
        cached = db.query(Recommendation).filter_by(
            format_point_id=format_point_id,
            recommendation_type="format_report",
        ).order_by(Recommendation.generated_at.desc()).first()
        if cached:
            return {"format_point": fp.name, **cached.content}

    # Get top 10 videos for this format point by views
    top_videos = (
        db.query(Video)
        .filter(Video.format_point_id == format_point_id, Video.analysis_status == "done")
        .order_by(Video.view_count.desc())
        .limit(10)
        .all()
    )

    if not top_videos:
        return {"format_point": fp.name, "error": "No analyzed videos yet for this format point"}

    # Build summary for Claude
    video_summaries = []
    avg_scores_accum = {str(i): [] for i in range(1, 25)}

    for v in top_videos:
        an = v.analysis
        summary = f"- '{v.title}' | {v.view_count:,} views | Channel: {v.channel_name}"
        if an:
            summary += f"\n  Concept: {an.concept_summary or 'N/A'}"
            for k, score in (an.format_point_scores or {}).items():
                if str(k) in avg_scores_accum:
                    avg_scores_accum[str(k)].append(score)
        video_summaries.append(summary)

    avg_scores = {k: round(sum(v) / len(v), 1) if v else 0 for k, v in avg_scores_accum.items()}

    prompt_result = analyzer.analyze_video.__func__  # just using the client directly
    # Actually call Claude for the report
    try:
        prompt = build_format_point_report_prompt(
            fp.name, fp.number, "\n".join(video_summaries), avg_scores
        )
        response = analyzer.client.messages.create(
            model=analyzer.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        import re
        match = re.search(r"\{[\s\S]+\}", raw)
        report_data = json.loads(match.group() if match else raw)
    except Exception as e:
        logger.error(f"Error generating format report: {e}")
        report_data = {}

    # Attach top videos data
    report_data["top_videos"] = [
        {
            "video_id": v.video_id,
            "title": v.title,
            "channel_name": v.channel_name,
            "view_count": v.view_count,
            "thumbnail_url": v.thumbnail_url,
            "concept_summary": v.analysis.concept_summary if v.analysis else None,
        }
        for v in top_videos
    ]

    # Cache in DB
    rec = Recommendation(
        format_point_id=format_point_id,
        recommendation_type="format_report",
        title=f"Report: {fp.name}",
        content=report_data,
    )
    db.add(rec)
    db.commit()

    return {"format_point": fp.name, **report_data}


def get_next_video_recommendations(db: Session, analyzer: ClaudeAnalyzer, regenerate: bool = False) -> dict:
    """Generate top 3 next video recommendations."""
    if not regenerate:
        cached = db.query(Recommendation).filter_by(
            recommendation_type="next_video",
        ).order_by(Recommendation.generated_at.desc()).first()
        if cached:
            return cached.content

    # Get top format points by avg views
    analyses = db.query(VideoAnalysis).join(Video).filter(Video.analysis_status == "done").all()
    if not analyses:
        return {"error": "No analyses available yet"}

    fp_view_map: dict[int, list] = {}
    fp_score_map: dict[int, list] = {}

    for an in analyses:
        for fp_num_str, score in (an.format_point_scores or {}).items():
            fp_num = int(fp_num_str)
            flag = (an.format_point_flags or {}).get(fp_num_str, False)
            if flag and an.video:
                fp_view_map.setdefault(fp_num, []).append(an.video.view_count or 0)
            fp_score_map.setdefault(fp_num, []).append(score)

    format_points = db.query(FormatPoint).all()
    fp_lookup = {fp.number: fp for fp in format_points}

    top_fp_data = []
    for fp_num, views in fp_view_map.items():
        avg_views = sum(views) / len(views) if views else 0
        scores = fp_score_map.get(fp_num, [0])
        top_score = max(scores)
        fp = fp_lookup.get(fp_num)
        if fp:
            top_fp_data.append({
                "number": fp_num,
                "name": fp.name,
                "avg_views": avg_views,
                "top_score": top_score,
            })

    top_fp_data.sort(key=lambda x: x["avg_views"], reverse=True)
    top_3 = top_fp_data[:5]

    # Extract trending topics
    topics = []
    for an in analyses[:100]:
        if an.health_niche_angle:
            topics.append(an.health_niche_angle)
    topic_counts = Counter(topics)
    trending = [t for t, _ in topic_counts.most_common(15)]

    try:
        prompt = build_next_video_prompt(top_3, trending, "Health / Nutrition / Wellness")
        response = analyzer.client.messages.create(
            model=analyzer.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        import re
        match = re.search(r"\{[\s\S]+\}", raw)
        result = json.loads(match.group() if match else raw)
    except Exception as e:
        logger.error(f"Error generating next video recommendations: {e}")
        result = {"error": str(e)}

    # Cache it
    rec = Recommendation(
        format_point_id=None,
        recommendation_type="next_video",
        title="Next Video Recommendations",
        content=result,
    )
    db.add(rec)
    db.commit()

    return result
