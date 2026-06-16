import { useEffect, useState } from 'react'
import axios from 'axios'
import { RefreshCw, Download, Lightbulb, TrendingUp, AlertTriangle, ArrowRight } from 'lucide-react'

const STATUS_COLORS = {
  HIGH_OPPORTUNITY: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  UNDERUSED: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  MODERATE: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  SATURATED_HIGH_PERFORMANCE: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  SATURATED_LOW_PERFORMANCE: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
}

function VideoRecommendation({ rec, index }) {
  const [expanded, setExpanded] = useState(index === 0)
  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full p-4 flex items-start gap-3 text-left hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
      >
        <span className="w-8 h-8 rounded-full bg-brand-500 text-white flex items-center justify-center text-sm font-bold shrink-0">
          {index + 1}
        </span>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="badge bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400">
              FP#{rec.format_point_number} — {rec.format_point_name}
            </span>
            <span className={`badge ${rec.estimated_view_potential === 'High' ? 'bg-green-100 text-green-700' : rec.estimated_view_potential === 'Medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-slate-100 text-slate-600'}`}>
              {rec.estimated_view_potential} potential
            </span>
          </div>
          <h3 className="font-semibold text-slate-900 dark:text-white mt-1 text-sm">{rec.suggested_title}</h3>
        </div>
        <ArrowRight size={16} className={`text-slate-400 transition-transform shrink-0 mt-1 ${expanded ? 'rotate-90' : ''}`} />
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-slate-100 dark:border-slate-700 pt-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">{rec.performance_rationale}</p>

          <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
            <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Hook (opening 15-30s)</p>
            <p className="text-xs text-slate-600 dark:text-slate-400 italic">"{rec.hook}"</p>
          </div>

          {rec.script_outline && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Script Outline</p>
              <div className="grid gap-2">
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded p-2">
                  <p className="text-xs font-medium text-blue-700 dark:text-blue-300">Intro (0-60s)</p>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">{rec.script_outline.intro}</p>
                </div>
                <div className="bg-slate-50 dark:bg-slate-700/50 rounded p-2">
                  <p className="text-xs font-medium text-slate-700 dark:text-slate-300">Body Sections</p>
                  <ol className="mt-0.5 space-y-0.5">
                    {(rec.script_outline.body_sections || []).map((s, i) => (
                      <li key={i} className="text-xs text-slate-600 dark:text-slate-400">{i+1}. {s}</li>
                    ))}
                  </ol>
                </div>
                <div className="bg-green-50 dark:bg-green-900/20 rounded p-2">
                  <p className="text-xs font-medium text-green-700 dark:text-green-300">CTA</p>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">{rec.script_outline.cta}</p>
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
            <Lightbulb size={11} />
            <span>Health topic: <strong>{rec.health_topic}</strong></span>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Recommendations() {
  const [nextVideo, setNextVideo] = useState(null)
  const [gapData, setGapData] = useState([])
  const [loadingNext, setLoadingNext] = useState(false)
  const [loadingGap, setLoadingGap] = useState(false)
  const [activeTab, setActiveTab] = useState('next_video')

  const loadNextVideo = (regenerate = false) => {
    setLoadingNext(true)
    axios.get('/api/recommendations/next-video', { params: { regenerate } })
      .then(r => { setNextVideo(r.data); setLoadingNext(false) })
      .catch(() => setLoadingNext(false))
  }

  useEffect(() => {
    // Auto-loading disabled — user must click "Generate" to load recommendations
    setLoadingNext(false)
    setLoadingGap(false)
  }, [])

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Recommendations</h1>
        <a href="/api/export/csv" className="btn-secondary flex items-center gap-2 text-sm">
          <Download size={14} /> Export CSV
        </a>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1 w-fit">
        {[
          { id: 'next_video', label: 'Next Video', Icon: Lightbulb },
          { id: 'gap_analysis', label: 'Gap Analysis', Icon: TrendingUp },
        ].map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === id
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {/* Next Video Tab */}
      {activeTab === 'next_video' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              AI-powered recommendations based on your analyzed videos
            </p>
            <button
              onClick={() => loadNextVideo(true)}
              disabled={loadingNext}
              className="btn-secondary flex items-center gap-1.5 text-sm"
            >
              <RefreshCw size={13} className={loadingNext ? 'animate-spin' : ''} />
              Regenerate
            </button>
          </div>

          {loadingNext ? (
            <div className="text-center py-12 text-slate-400">Generating recommendations with AI...</div>
          ) : !nextVideo ? (
            <div className="card p-10 text-center">
              <Lightbulb size={36} className="mx-auto text-slate-300 dark:text-slate-600 mb-3" />
              <p className="text-slate-500 dark:text-slate-400 font-medium">Recommendations not loaded yet</p>
              <p className="text-xs text-slate-400 mt-1 mb-4">Click Generate to get AI-powered video recommendations based on your competitor data.</p>
              <button onClick={() => loadNextVideo(false)} className="btn-primary text-sm">
                Generate Recommendations
              </button>
            </div>
          ) : nextVideo?.error ? (
            <div className="card p-6 text-center">
              <AlertTriangle size={32} className="mx-auto text-yellow-400 mb-3" />
              <p className="text-slate-500 dark:text-slate-400">{nextVideo.error}</p>
              <p className="text-xs text-slate-400 mt-1">Analyze some videos first to get recommendations.</p>
            </div>
          ) : (
            <>
              {(nextVideo?.recommendations || []).map((rec, i) => (
                <VideoRecommendation key={i} rec={rec} index={i} />
              ))}

              {nextVideo?.trending_topics_to_cover?.length > 0 && (
                <div className="card p-4">
                  <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-2 text-sm flex items-center gap-1.5">
                    <TrendingUp size={14} /> Trending Topics to Cover
                  </h2>
                  <div className="flex flex-wrap gap-2">
                    {nextVideo.trending_topics_to_cover.map((t, i) => (
                      <span key={i} className="badge bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {nextVideo?.format_combinations?.length > 0 && (
                <div className="card p-4">
                  <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-2 text-sm">Winning Format Combinations</h2>
                  <div className="space-y-2">
                    {nextVideo.format_combinations.map((combo, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <div className="flex gap-1">
                          {(combo.formats || []).map(f => (
                            <span key={f} className="badge bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400">FP{f}</span>
                          ))}
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400">{combo.rationale}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Gap Analysis Tab */}
      {activeTab === 'gap_analysis' && (
        <div className="space-y-3">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Opportunity analysis across all format points
          </p>
          {loadingGap ? (
            <div className="text-center py-12 text-slate-400">Calculating gap analysis...</div>
          ) : gapData.length === 0 ? (
            <div className="card p-6 text-center text-slate-400">No data yet. Scrape and analyze videos first.</div>
          ) : (
            <div className="card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                      {['#', 'Format Point', 'Avg Score', 'Videos Using', 'Avg Views', 'Saturation', 'Status'].map(h => (
                        <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {gapData.map((row, i) => (
                      <tr key={row.format_point_id} className={`border-b border-slate-100 dark:border-slate-700/50 ${i % 2 === 0 ? '' : 'bg-slate-50/50 dark:bg-slate-800/20'}`}>
                        <td className="px-4 py-2.5 text-slate-400 text-xs">{row.format_point_number}</td>
                        <td className="px-4 py-2.5 font-medium text-slate-800 dark:text-slate-200">{row.format_point_name}</td>
                        <td className="px-4 py-2.5 text-slate-600 dark:text-slate-400">{row.avg_score}/10</td>
                        <td className="px-4 py-2.5 text-slate-600 dark:text-slate-400">{row.videos_using}</td>
                        <td className="px-4 py-2.5 text-slate-600 dark:text-slate-400">{row.avg_views_when_used?.toLocaleString()}</td>
                        <td className="px-4 py-2.5 text-slate-600 dark:text-slate-400">{row.competitor_saturation_pct}%</td>
                        <td className="px-4 py-2.5">
                          <span className={`badge ${STATUS_COLORS[row.status] || 'bg-slate-100 text-slate-600'}`}>
                            {row.status?.replace(/_/g, ' ')}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
