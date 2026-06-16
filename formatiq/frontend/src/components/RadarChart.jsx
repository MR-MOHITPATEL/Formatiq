import {
  RadarChart as ReRadarChart, PolarGrid, PolarAngleAxis,
  Radar, ResponsiveContainer, Tooltip
} from 'recharts'

const FORMAT_POINT_NAMES = {
  1: 'A vs B', 2: 'Underdog', 3: 'DYK Fact', 4: 'Tips',
  5: 'Is This You', 6: "You're Wrong", 7: 'Patient', 8: 'Concoction',
  9: 'DYK Villain', 10: 'Villain', 11: 'Ingredient', 12: 'DIY Goal',
  13: 'Current+DIY', 14: 'Rating', 15: 'Reels Tips', 16: 'How To',
  17: 'Products', 18: 'Supplements', 19: 'Diagnosis', 20: 'CGM',
  21: 'Podcast', 22: 'Reversal', 23: 'Reaction', 24: 'Contact'
}

export default function RadarChart({ scores }) {
  if (!scores || Object.keys(scores).length === 0) return null

  // Use top 12 scoring categories for readable radar
  const sorted = Object.entries(scores)
    .map(([k, v]) => ({ fp: Number(k), score: v }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 12)

  const data = sorted.map(({ fp, score }) => ({
    subject: FORMAT_POINT_NAMES[fp] || `FP${fp}`,
    score,
    fullMark: 10,
  }))

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ReRadarChart data={data}>
        <PolarGrid stroke="#e2e8f0" />
        <PolarAngleAxis
          dataKey="subject"
          tick={{ fontSize: 10, fill: '#64748b' }}
        />
        <Radar
          name="Score"
          dataKey="score"
          stroke="#6366f1"
          fill="#6366f1"
          fillOpacity={0.25}
          strokeWidth={2}
        />
        <Tooltip
          formatter={(value) => [`${value}/10`, 'Score']}
          contentStyle={{
            backgroundColor: '#1e293b',
            border: 'none',
            borderRadius: '8px',
            color: '#f1f5f9',
            fontSize: 12,
          }}
        />
      </ReRadarChart>
    </ResponsiveContainer>
  )
}
