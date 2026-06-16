# FormatIQ — YouTube Research & Strategy System

A full-stack research tool for Health/Nutrition/Wellness YouTube creators to analyze competitor videos across 24 video format types, get AI-powered script recommendations, and find content gaps.

---

## Features

- **Scrape** 50–100 videos per format point via YouTube Data API
- **Extract transcripts** automatically (with auto-caption fallback)
- **AI analysis** via Claude — concept summaries, script structure, 24-point scoring
- **Recommendations** — what to make next, with script outlines and hooks
- **Gap analysis** — which format types competitors underuse
- **Export** — CSV and PDF reports per format point
- **Dashboard** — React + Tailwind with dark mode, radar charts, bar charts

---

## Quick Start (Windows)

```
double-click run.bat
```

This installs all dependencies and opens both servers.

**Linux / Mac:**
```bash
chmod +x run.sh
./run.sh
```

Then open: **http://localhost:5173**

---

## Manual Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- A YouTube Data API v3 key
- An Anthropic API key

---

### Step 1 — Get a YouTube Data API key

1. Go to https://console.cloud.google.com/
2. Create a new project (or select existing)
3. Go to **APIs & Services → Library**
4. Search for **YouTube Data API v3** and enable it
5. Go to **APIs & Services → Credentials**
6. Click **Create Credentials → API Key**
7. Copy the key

> **Note:** Free tier = 10,000 quota units/day. Each search costs 100 units; each video detail fetch costs 1 unit. With 50 videos/format point × 24 formats = ~2,450 units/day for scraping.

---

### Step 2 — Get an Anthropic API key

1. Go to https://console.anthropic.com/
2. Sign in or create account
3. Go to **API Keys** and create a new key
4. Copy the key

> **Cost estimate:** ~$0.05–0.15 per video analyzed (depends on transcript length). 100 videos ≈ $5–15.

---

### Step 3 — Configure

Edit `backend/config.yaml`:

```yaml
youtube_api_key: "YOUR_KEY_HERE"
anthropic_api_key: "YOUR_KEY_HERE"

competitor_channels:
  - "UCxxxxxxxxxxxxxxxxxxxxxxx"    # Paste channel IDs here
  - "https://www.youtube.com/@ChannelName"

videos_per_format_point: 50
niche: "Health / Nutrition / Wellness"
```

---

### Step 4 — Install dependencies

**Backend:**
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r ../requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

---

### Step 5 — Run

**Backend (in one terminal):**
```bash
cd backend
# activate venv first
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend (in another terminal):**
```bash
cd frontend
npm run dev
```

Open: **http://localhost:5173**

---

## Usage Workflow

### 1. Configure channels (Controls page)
Add competitor channel IDs or URLs. These will be scraped alongside keyword searches.

### 2. Run Scraper (Controls page)
- Select which format points to scrape (or leave blank for all 24)
- Set videos per format point (50 recommended to start)
- Click **Start Scraping**
- Progress tracked in real-time

### 3. Run Analysis (Controls page)
- Select format point (optional — analyze all by default)
- Check the **estimated cost** before running
- Click **Start Analysis**
- Claude analyzes each video's title, description, and transcript

### 4. Browse Results
- **Format Points page** — browse all 24 types, filter by views/channel
- **Video Detail page** — full analysis, radar chart, script excerpts
- **Recommendations page** — AI-generated "make this next" + gap analysis

### 5. Export
- CSV export on every page (all metadata + 24 format point scores)
- PDF report per format point (top 10 videos, script excerpts)

---

## Project Structure

```
formatiq/
├── backend/
│   ├── main.py                  # FastAPI app + all endpoints
│   ├── config.yaml              # User configuration
│   ├── config.py                # Config loader
│   ├── database.py              # SQLAlchemy models + DB init
│   ├── scraper/
│   │   ├── youtube_scraper.py   # YouTube Data API scraping
│   │   ├── transcript.py        # Transcript extraction
│   │   └── keyword_gen.py       # Auto-generated keywords per format
│   ├── analyzer/
│   │   ├── claude_analyzer.py   # Claude API calls
│   │   ├── batch_processor.py   # Batch processing + resume
│   │   └── prompts.py           # All Claude prompts
│   ├── recommender/
│   │   ├── recommendation.py    # Format reports + next video ideas
│   │   └── gap_analysis.py      # Competitor gap analysis
│   └── exporters/
│       ├── csv_export.py        # CSV generation
│       └── pdf_export.py        # PDF report generation
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Overview.jsx     # Dashboard with stats + charts
│       │   ├── FormatPoints.jsx # 24-format browser + video grid
│       │   ├── VideoDetail.jsx  # Full video analysis view
│       │   ├── Recommendations.jsx # Next video + gap analysis
│       │   └── Controls.jsx     # Scrape/analyze controls
│       └── components/
│           ├── VideoCard.jsx    # Reusable video thumbnail card
│           ├── RadarChart.jsx   # 24-point radar chart
│           ├── ScoreBar.jsx     # Score progress bar
│           └── Navbar.jsx       # Top navigation
├── requirements.txt
├── run.sh                       # Unix startup script
├── run.bat                      # Windows startup script
└── README.md
```

---

## The 24 Format Points

| # | Name | Description |
|---|------|-------------|
| 1 | A vs B | Comparison-style video |
| 2 | Underdog to Hero | Transformation narrative |
| 3 | DYK - Fact | Did You Know, fact-based |
| 4 | Tips | Listicle / tips format |
| 5 | Is this You? | Relatable problem opener |
| 6 | You're Wrong | Myth-busting |
| 7 | Patient Problem | Case study as hook |
| 8 | Concoction | Secret recipe reveal |
| 9 | DYK Villain | Bad habits as villain |
| 10 | Villain Based | Ingredient as villain |
| 11 | Natural Ingredient | Food ingredient spotlight |
| 12 | DIY Goal | Goal-oriented tutorial |
| 13 | Current Affair+DIY | Trending news + DIY |
| 14 | Ingredient Rating | Rating system |
| 15 | Reels/Tips | Short-form style |
| 16 | How To+DIY | How-to with hands-on |
| 17 | Product Rating | Branded product review |
| 18 | Supplement Rec | Chemical supplement breakdown |
| 19 | Diagnosis | Assessment style |
| 20 | CGM Format | Glucose monitor data |
| 21 | Podcast Split | Long-form excerpt |
| 22 | Reversal | Recovery story |
| 23 | Reaction | Creator reacts |
| 24 | Invite to Contact | CTA-heavy |

---

## API Reference

The FastAPI backend exposes these endpoints (full docs at http://localhost:8000/docs):

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/overview` | Dashboard stats |
| GET | `/api/format-points` | List all 24 format points |
| GET | `/api/format-points/{id}/videos` | Videos for a format point |
| GET | `/api/videos/{video_id}` | Full video detail + analysis |
| GET | `/api/recommendations/next-video` | AI next video recommendations |
| GET | `/api/recommendations/gap-analysis` | Competitor gap analysis |
| GET | `/api/recommendations/format-report/{id}` | Format point report |
| POST | `/api/scrape/start` | Start scraping job |
| POST | `/api/analyze/start` | Start analysis batch |
| GET | `/api/jobs/{job_id}` | Check job progress |
| GET | `/api/channels` | List competitor channels |
| POST | `/api/channels` | Add competitor channel |
| GET | `/api/export/csv` | Export all videos as CSV |
| GET | `/api/export/csv/{fp_id}` | Export format point as CSV |
| GET | `/api/export/pdf/{fp_id}` | Export format point as PDF |

---

## Adding More Format Points

Edit `database.py` — add entries to `FORMAT_POINTS_SEED` and update the keyword defaults in `scraper/keyword_gen.py`. The system is designed to handle any number of format points.

---

## Troubleshooting

**"YouTube quota exceeded"**
The API has a 10,000 unit/day limit. Each search = 100 units. Scrape in smaller batches or spread across days.

**"Transcript not available"**
Some videos disable transcripts. The analyzer will still work using title + description only.

**"Analysis failed"**
Check your Anthropic API key in config.yaml. Failed videos can be re-run — the batch processor skips already-analyzed videos.

**Frontend shows "Failed to load"**
Make sure the backend is running on port 8000. Check backend logs for errors.
