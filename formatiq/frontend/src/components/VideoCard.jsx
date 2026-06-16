import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Eye, ThumbsUp, Swords, CheckCircle, RefreshCw } from 'lucide-react'

function fmtViews(n) {
  if (!n) return '0'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(0) + 'K'
  return String(n)
}

function fmtDuration(secs) {
  if (!secs) return ''
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

const STATUS_COLORS = {
  done: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
  pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400',
  analyzing: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
}

export default function VideoCard({ video }) {
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzed, setAnalyzed] = useState(video.has_angle_analysis || false)

  const topScores = Object.entries(video.top_format_scores || {})
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3)

  const handleAnalyze = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    setAnalyzing(true)
    try {
      await fetch(`/api/videos/${video.video_id}/analyze-angles`, { method: 'POST' })
      setAnalyzed(true)
    } catch (_) {}
    finally { setAnalyzing(false) }
  }

  return (
    <Link to={`/video/${video.video_id}`} className="card hover:shadow-md transition-shadow block">
      {/* Thumbnail */}
      <div className="relative">
        <img
          src={video.thumbnail_url || `https://img.youtube.com/vi/${video.video_id}/mqdefault.jpg`}
          alt={video.title}
          className="w-full aspect-video object-cover rounded-t-xl"
          loading="lazy"
        />
        {video.duration_seconds > 0 && (
          <span className="absolute bottom-1 right-1 bg-black/80 text-white text-xs px-1 rounded">
            {fmtDuration(video.duration_seconds)}
          </span>
        )}
        <span className={`absolute top-1 left-1 badge ${STATUS_COLORS[video.analysis_status] || STATUS_COLORS.pending}`}>
          {video.analysis_status}
        </span>
        <button
          onClick={handleAnalyze}
          disabled={analyzing}
          title="Analyze 5 Angles with Gemini"
          className={`absolute top-1 right-1 flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium transition-colors ${
            analyzed
              ? 'bg-green-500/90 text-white'
              : 'bg-black/70 text-white hover:bg-brand-500/90'
          }`}
        >
          {analyzing ? <RefreshCw size={10} className="animate-spin" /> : analyzed ? <CheckCircle size={10} /> : <Swords size={10} />}
          {analyzing ? '' : analyzed ? '5✓' : '5-Angle'}
        </button>
      </div>

      <div className="p-3">
        <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100 line-clamp-2 mb-1">
          {video.title}
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">{video.channel_name}</p>

        <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1"><Eye size={11} />{fmtViews(video.view_count)}</span>
          {video.like_count > 0 && (
            <span className="flex items-center gap-1"><ThumbsUp size={11} />{fmtViews(video.like_count)}</span>
          )}
        </div>

        {topScores.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {topScores.map(([fpNum, score]) => (
              <span key={fpNum} className="badge bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400">
                FP{fpNum}: {score}/10
              </span>
            ))}
          </div>
        )}
      </div>
    </Link>
  )
}
