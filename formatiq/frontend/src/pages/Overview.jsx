import { useEffect, useState } from 'react'
import axios from 'axios'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Video, BarChart2, Users, CheckCircle, Clock, Download } from 'lucide-react'
import VideoCard from '../components/VideoCard.jsx'

function StatCard({ icon: Icon, label, value, sub, color = 'brand' }) {
  return (
    <div className="card p-4 flex items-start gap-3">
      <div className={`p-2 rounded-lg bg-${color}-50 dark:bg-${color}-900/30`}>
        <Icon size={18} className={`text-${color}-600 dark:text-${color}-400`} />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-900 dark:text-white">{value?.toLocaleString()}</p>
        <p className="text-sm font-medium text-slate-600 dark:text-slate-400">{label}</p>
        {sub && <p className="text-xs text-slate-400 dark:text-slate-500">{sub}</p>}
      </div>
    </div>
  )
}

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe']

export default function Overview() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios.get('/api/overview').then(r => { setData(r.data); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>
  if (!data) return <div className="text-red-500 p-4">Failed to load overview. Is the backend running?</div>

  const chartData = (data.format_point_stats || [])
    .slice(0, 24)
    .map(fp => ({ name: `FP${fp.number}`, views: fp.avg_views, fullName: fp.name }))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">FormatIQ Dashboard</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">Health / Nutrition / Wellness — YouTube Research</p>
        </div>
        <a href="/api/export/csv" className="btn-secondary flex items-center gap-2 text-sm">
          <Download size={14} /> Export All CSV
        </a>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={Video} label="Total Videos" value={data.total_videos} color="brand" />
        <StatCard icon={CheckCircle} label="Analyzed" value={data.analyzed_videos} color="green" />
        <StatCard icon={Clock} label="Pending" value={data.pending_videos} color="yellow" />
        <StatCard icon={Users} label="Channels" value={data.total_channels} color="purple" />
      </div>

      {/* Bar chart */}
      <div className="card p-5">
        <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-4">Avg Views by Format Point</h2>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}K` : v} />
              <Tooltip
                formatter={(v, _, props) => [`${v?.toLocaleString()} avg views`, props.payload?.fullName || '']}
                contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f1f5f9', fontSize: 12 }}
              />
              <Bar dataKey="views" radius={[4, 4, 0, 0]}>
                {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-slate-400 text-sm text-center py-12">No data yet. Run the scraper to get started.</p>
        )}
      </div>

      {/* Recent analyses */}
      {data.recent_analyses?.length > 0 && (
        <div>
          <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-3">Recently Analyzed</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {data.recent_analyses.map(v => <VideoCard key={v.video_id} video={v} />)}
          </div>
        </div>
      )}

      {data.total_videos === 0 && (
        <div className="card p-8 text-center">
          <BarChart2 size={40} className="mx-auto text-slate-300 dark:text-slate-600 mb-3" />
          <h3 className="font-semibold text-slate-700 dark:text-slate-300 mb-1">No data yet</h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            Go to <strong>Controls</strong> to configure your API keys and start scraping.
          </p>
        </div>
      )}
    </div>
  )
}
