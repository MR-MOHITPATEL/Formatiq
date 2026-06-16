from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float,
    DateTime, Boolean, ForeignKey, JSON, text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Production: DATABASE_URL env var (Supabase PostgreSQL)
# Local dev: SQLite file
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, 'formatiq.db')}"
)

# Supabase gives "postgres://" but SQLAlchemy needs "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

IS_POSTGRES = DATABASE_URL.startswith("postgresql")

if IS_POSTGRES:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class FormatPoint(Base):
    __tablename__ = "format_points"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    keywords = Column(JSON, default=list)  # auto-generated keywords
    custom_keywords = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    videos = relationship("Video", back_populates="format_point")


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String(100), unique=True, nullable=False)
    channel_name = Column(String(300))
    channel_url = Column(String(500))
    subscriber_count = Column(Integer)
    is_competitor = Column(Boolean, default=True)
    # "direct" = primary benchmarked competitors, "market" = broader pool, "own" = user's channel
    competitor_tier = Column(String(20), default="market")
    added_at = Column(DateTime, default=datetime.utcnow)

    videos = relationship("Video", back_populates="channel")


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(50), unique=True, nullable=False)
    title = Column(String(500))
    description = Column(Text)
    thumbnail_url = Column(String(500))
    channel_id = Column(Integer, ForeignKey("channels.id"))
    channel_name = Column(String(300))
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    published_at = Column(DateTime)
    duration = Column(String(50))
    duration_seconds = Column(Integer)
    transcript = Column(Text)
    transcript_available = Column(Boolean, default=False)
    format_point_id = Column(Integer, ForeignKey("format_points.id"))
    scraped_at = Column(DateTime, default=datetime.utcnow)
    analysis_status = Column(String(20), default="pending")  # pending, analyzing, done, failed
    video_type = Column(String(10), default="longform")  # "short" | "longform"

    channel = relationship("Channel", back_populates="videos")
    format_point = relationship("FormatPoint", back_populates="videos")
    analysis = relationship("VideoAnalysis", back_populates="video", uselist=False)
    angle_analysis = relationship("VideoAngleAnalysis", back_populates="video", uselist=False)


class VideoAngleAnalysis(Base):
    __tablename__ = "video_angle_analyses"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), unique=True)

    villain_present = Column(Boolean, default=False)
    villain_description = Column(Text)
    villain_exact_lines = Column(JSON)

    hero_present = Column(Boolean, default=False)
    hero_description = Column(Text)
    hero_exact_lines = Column(JSON)

    virality_present = Column(Boolean, default=False)
    virality_description = Column(Text)
    virality_exact_lines = Column(JSON)

    credibility_present = Column(Boolean, default=False)
    credibility_description = Column(Text)
    credibility_exact_lines = Column(JSON)

    moral_ground_present = Column(Boolean, default=False)
    moral_ground_description = Column(Text)
    moral_ground_exact_lines = Column(JSON)

    format_point_mapping = Column(JSON)   # {fp_number: rationale string}
    overall_strength = Column(Integer)    # 1-10

    analyzed_at = Column(DateTime, default=datetime.utcnow)
    model_used = Column(String(100))

    video = relationship("Video", back_populates="angle_analysis")


class VideoAnalysis(Base):
    __tablename__ = "video_analyses"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), unique=True)
    concept_summary = Column(Text)
    script_analysis = Column(Text)
    format_point_scores = Column(JSON)   # {format_point_id: score (0-10)}
    format_point_flags = Column(JSON)    # {format_point_id: bool}
    best_moments = Column(JSON)          # list of {timestamp, excerpt, note}
    what_works = Column(JSON)            # list of strings
    what_doesnt_work = Column(JSON)      # list of strings
    health_niche_angle = Column(Text)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    model_used = Column(String(100))
    tokens_used = Column(Integer, default=0)

    video = relationship("Video", back_populates="analysis")


class ChannelStyleProfile(Base):
    __tablename__ = "channel_style_profiles"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), unique=True)
    tone_description = Column(Text)       # how the creator speaks
    vocabulary_notes = Column(Text)       # words/phrases they use or avoid
    script_structure = Column(Text)       # typical hook/intro/body/cta pattern
    topics_covered = Column(JSON)         # list of topics already made videos on
    credibility_signals = Column(Text)    # how they cite sources, disclaimer style
    raw_profile = Column(JSON)            # full Gemini output
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    model_used = Column(String(100))
    videos_analyzed = Column(Integer, default=0)

    channel = relationship("Channel")


class GeneratedScript(Base):
    __tablename__ = "generated_scripts"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(500), nullable=False)
    angle = Column(Text)
    format_type = Column(String(20), nullable=False)  # "shorts" | "longform"
    validated = Column(Boolean, default=False)
    validation_result = Column(JSON)   # {direct_validated, market_validated, go, evidence}
    trending_sources = Column(JSON)    # list of source names used
    full_script = Column(Text)
    outline = Column(Text)
    citations = Column(JSON)           # list of {claim, source_name, url, published}
    language = Column(String(20), default="hinglish")  # "english" | "hinglish" | "hindi"
    created_at = Column(DateTime, default=datetime.utcnow)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    format_point_id = Column(Integer, ForeignKey("format_points.id"))
    recommendation_type = Column(String(50))  # next_video, gap_analysis, format_report
    title = Column(String(500))
    content = Column(JSON)
    generated_at = Column(DateTime, default=datetime.utcnow)

    format_point = relationship("FormatPoint")


FORMAT_POINTS_SEED = [
    (1, "A vs B", "Comparison-style video (e.g., India vs Pakistan style)"),
    (2, "Underdog to Hero", "Transformation/journey narrative"),
    (3, "DYK - Fact", "Did You Know fact-based educational video"),
    (4, "Tips", "Tips-based listicle format"),
    (5, "Is this You / Does it happen to you?", "Relatable problem identification opener"),
    (6, "If you think so, You are wrong", "Myth-busting / counter-intuitive revelation"),
    (7, "Patient problem opener", "Specific case study or patient story as hook"),
    (8, "Concoction / Secret Mix", "Secret recipe or mix with benefits reveal"),
    (9, "DYK Villain - habit/symptom", "Did You Know villain focused on bad habits/symptoms"),
    (10, "Villain based", "Ingredient or intent-based villain narrative"),
    (11, "Natural Ingredient centric", "Food/natural ingredient spotlight video"),
    (12, "DIY - Goal based", "Do It Yourself goal-oriented tutorial"),
    (13, "Current Affair + DIY", "Trending topic combined with DIY recommendation"),
    (14, "Ingredient/Compound rating", "Rating system with rationale for ingredients"),
    (15, "IG Reels type - Tips/DOs DONTs", "Short-form style with tips, dos and don'ts"),
    (16, "How to? with DIY", "How-to tutorial with hands-on DIY component"),
    (17, "Product ratings", "Product review and rating (including branded)"),
    (18, "Supplement Recommendations", "Chemical/synthetic supplement benefits breakdown"),
    (19, "Diagnosis", "Diagnostic/assessment style video"),
    (20, "CGM Format", "Continuous Glucose Monitor data-driven format"),
    (21, "Podcast split videos", "Long-form podcast excerpt (TRS style)"),
    (22, "Reversal", "Reversal/recovery story format"),
    (23, "Reaction Videos", "Creator reacts to content, trends, or studies"),
    (24, "Invite to contact", "CTA-heavy video inviting viewer engagement/contact"),
]


def _run_migrations(conn):
    """Apply schema changes that create_all won't handle (new columns on existing tables)."""
    migrations = [
        "ALTER TABLE channels ADD COLUMN competitor_tier VARCHAR(20) DEFAULT 'market'",
        "ALTER TABLE generated_scripts ADD COLUMN citations TEXT",
        "ALTER TABLE generated_scripts ADD COLUMN language VARCHAR(20) DEFAULT 'hinglish'",
        "ALTER TABLE videos ADD COLUMN video_type VARCHAR(10) DEFAULT 'longform'",
    ]
    for sql in migrations:
        try:
            conn.execute(text(sql))
            conn.commit()
        except Exception:
            conn.rollback()  # column already exists — safe to ignore (both SQLite and PostgreSQL)


def init_db():
    Base.metadata.create_all(bind=engine)

    # Run ALTER TABLE migrations for columns added to existing tables
    with engine.connect() as conn:
        _run_migrations(conn)

    db = SessionLocal()
    try:
        if db.query(FormatPoint).count() == 0:
            for num, name, desc in FORMAT_POINTS_SEED:
                fp = FormatPoint(number=num, name=name, description=desc)
                db.add(fp)
            db.commit()
            print(f"Seeded {len(FORMAT_POINTS_SEED)} format points.")
    finally:
        db.close()
