"""
Batch processing of video analysis with progress tracking and resume support.
"""
import logging
import time
from sqlalchemy.orm import Session

from database import Video, VideoAnalysis
from analyzer.claude_analyzer import ClaudeAnalyzer

logger = logging.getLogger(__name__)


def process_batch(
    db: Session,
    analyzer: ClaudeAnalyzer,
    batch_size: int = 10,
    format_point_id: int | None = None,
    progress_callback=None,
) -> dict:
    """
    Analyze pending videos in batches. Skips already-analyzed videos.
    Returns summary dict with counts and tokens used.
    """
    query = db.query(Video).filter(Video.analysis_status == "pending")
    if format_point_id:
        query = query.filter(Video.format_point_id == format_point_id)

    pending_videos = query.all()
    total = len(pending_videos)

    if total == 0:
        return {"total": 0, "analyzed": 0, "failed": 0, "tokens_used": 0}

    analyzed = 0
    failed = 0

    for i in range(0, total, batch_size):
        batch = pending_videos[i:i + batch_size]

        for j, video in enumerate(batch):
            global_idx = i + j + 1

            try:
                video.analysis_status = "analyzing"
                db.commit()

                result = analyzer.analyze_video(
                    title=video.title or "",
                    description=video.description or "",
                    transcript=video.transcript,
                    channel_name=video.channel_name or "",
                    view_count=video.view_count or 0,
                )

                if result:
                    _save_analysis(db, video, result)
                    video.analysis_status = "done"
                    analyzed += 1
                else:
                    video.analysis_status = "failed"
                    failed += 1

                db.commit()

            except Exception as e:
                logger.error(f"Error processing video {video.video_id}: {e}")
                video.analysis_status = "failed"
                db.commit()
                failed += 1

            if progress_callback:
                progress_callback(global_idx, total, video.title or video.video_id)

            time.sleep(0.5)  # Be gentle with API

        # Pause between batches
        if i + batch_size < total:
            time.sleep(2)

    return {
        "total": total,
        "analyzed": analyzed,
        "failed": failed,
        "tokens_used": analyzer.total_tokens,
    }


def _save_analysis(db: Session, video: Video, result: dict):
    """Persist analysis result to VideoAnalysis table."""
    existing = db.query(VideoAnalysis).filter_by(video_id=video.id).first()

    # Convert string keys to int in scores/flags
    scores = {int(k): v for k, v in result.get("format_point_scores", {}).items()}
    flags = {int(k): v for k, v in result.get("format_point_flags", {}).items()}

    if existing:
        existing.concept_summary = result.get("concept_summary")
        existing.script_analysis = result.get("script_analysis")
        existing.format_point_scores = scores
        existing.format_point_flags = flags
        existing.best_moments = result.get("best_moments", [])
        existing.what_works = result.get("what_works", [])
        existing.what_doesnt_work = result.get("what_doesnt_work", [])
        existing.health_niche_angle = result.get("health_niche_angle")
        existing.tokens_used = result.get("_tokens_used", 0)
    else:
        analysis = VideoAnalysis(
            video_id=video.id,
            concept_summary=result.get("concept_summary"),
            script_analysis=result.get("script_analysis"),
            format_point_scores=scores,
            format_point_flags=flags,
            best_moments=result.get("best_moments", []),
            what_works=result.get("what_works", []),
            what_doesnt_work=result.get("what_doesnt_work", []),
            health_niche_angle=result.get("health_niche_angle"),
            model_used=result.get("model_used", ""),
            tokens_used=result.get("_tokens_used", 0),
        )
        db.add(analysis)
