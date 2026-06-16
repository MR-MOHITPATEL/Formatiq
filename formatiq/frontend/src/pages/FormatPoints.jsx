import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { Download, Filter, ArrowLeft, FileText } from 'lucide-react'
import VideoCard from '../components/VideoCard.jsx'

function FormatPointCard({ fp, onClick, active }) {
  return (
    <button
      onClick={() => onClick(fp)}
      className={`card p-4 text-left hover:shadow-md transition-all ${active ? 'ring-2 ring-brand-500' : ''}`}
    >
      <div className="flex items-start justify-between mb-2">
        <span className="badge bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400">
          #{fp.number}
        </span>
        <span className="text-xs text-slate-400 dark:text-slate-500">{fp.video_count} videos</span>
      </div>
      <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-1">{fp.name}</h3>
      <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2">{fp.description}</p>
      <div className="mt-3 flex items-center gap-3 text-xs">
        <span className="text-slate-600 dark:text-slate-400">
          {fp.avg_views?.toLocaleString()} avg views
        </span>
        <span className="text-green-600 dark:text-green-400">{fp.analyzed_count} analyzed</span>
      </div>
    </button>
  )
}

export default function FormatPoints() {
  const { fpId } = useParams()
  const navigate = useNavigate()
  const [formatPoints, setFormatPoints] = useState([])
  const [selectedFp, setSelectedFp] = useState(null)
  const [videos, setVideos] = useState([])
  const [totalVideos, setTotalVideos] = useState(0)
  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = useState('view_count')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    axios.get('/api/format-points').then(r => {
      setFormatPoints(r.data)
      if (fpId) {
        const fp = r.data.find(f => f.id === Number(fpId))
        if (fp) setSelectedFp(fp)
      }
    })
  }, [])

  useEffect(() => {
    if (!selectedFp) return
    setLoading(true)
    axios.get(`/api/format-points/${selectedFp.id}/videos`, {
      params: { sort_by: sortBy, page, page_size: 20 }
    }).then(r => {
      setVideos(r.data.videos)
      setTotalVideos(r.data.total)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [selectedFp, sortBy, page])

  const handleSelectFp = (fp) => {
    setSelectedFp(fp)
    setPage(1)
    navigate(`/format-points/${fp.id}`)
  }

  if (selectedFp) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <button onClick={() => { setSelectedFp(null); navigate('/format-points') }} className="btn-secondary flex items-center gap-1 text-sm">
            <ArrowLeft size={14} /> Back
          </button>
          <div className="flex-1">
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">
              #{selectedFp.number} — {selectedFp.name}
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">{selectedFp.description}</p>
          </div>
          <a href={`/api/export/csv/${selectedFp.id}`} className="btn-secondary flex items-center gap-1 text-sm">
            <Download size={13} /> CSV
          </a>
          <a href={`/api/export/pdf/${selectedFp.id}`} className="btn-secondary flex items-center gap-1 text-sm">
            <FileText size={13} /> PDF
          </a>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <Filter size={14} className="text-slate-400" />
          <span className="text-sm text-slate-600 dark:text-slate-400">{totalVideos} videos</span>
          <select
            value={sortBy}
            onChange={e => { setSortBy(e.target.value); setPage(1) }}
            className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300"
          >
            <option value="view_count">Sort: Views</option>
            <option value="published_at">Sort: Newest</option>
          </select>
        </div>

        {loading ? (
          <div className="text-center py-12 text-slate-400">Loading videos...</div>
        ) : videos.length === 0 ? (
          <div className="card p-8 text-center text-slate-400">
            No videos scraped for this format point yet.
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {videos.map(v => <VideoCard key={v.video_id} video={v} />)}
          </div>
        )}

        {/* Pagination */}
        {totalVideos > 20 && (
          <div className="flex justify-center gap-2 pt-2">
            <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="btn-secondary text-sm disabled:opacity-40">Prev</button>
            <span className="text-sm text-slate-500 flex items-center">Page {page} of {Math.ceil(totalVideos / 20)}</span>
            <button disabled={page >= Math.ceil(totalVideos / 20)} onClick={() => setPage(p => p + 1)} className="btn-secondary text-sm disabled:opacity-40">Next</button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Format Points Browser</h1>
      <p className="text-slate-500 dark:text-slate-400 text-sm">
        {formatPoints.length} format types — click any to explore videos
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
        {formatPoints.map(fp => (
          <FormatPointCard key={fp.id} fp={fp} onClick={handleSelectFp} active={selectedFp?.id === fp.id} />
        ))}
      </div>
    </div>
  )
}
