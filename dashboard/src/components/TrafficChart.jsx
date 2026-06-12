// src/components/TrafficChart.jsx

/**
 * Live line chart showing total wait time over simulation steps.
 * Uses Recharts library.
 */

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend
} from 'recharts'

// Custom tooltip for the chart
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-panel border border-elevated rounded-lg p-3 text-xs font-mono">
      <p className="text-muted mb-1">Step {label}</p>
      {payload.map(p => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {Math.round(p.value)}s
        </p>
      ))}
    </div>
  )
}

export default function TrafficChart({ history }) {
  // Format data for recharts
  const chartData = history.map(h => ({
    step:       h.step,
    total_wait: Math.round(h.total_wait ?? 0),
    north:      Math.round(h.wait?.north ?? 0),
    south:      Math.round(h.wait?.south ?? 0),
    east:       Math.round(h.wait?.east  ?? 0),
    west:       Math.round(h.wait?.west  ?? 0),
  }))

  if (chartData.length === 0) {
    return (
      <div className="bg-panel rounded-xl p-4 border border-elevated h-64
                      flex items-center justify-center">
        <p className="text-muted text-sm">Waiting for data...</p>
      </div>
    )
  }

  return (
    <div className="bg-panel rounded-xl p-4 border border-elevated">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">
          Wait Time — Live
        </h3>
        <span className="text-xs text-muted font-mono">
          {chartData.length} steps
        </span>
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData}
                   margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1E293B"/>
          <XAxis dataKey="step" tick={{ fill: '#94A3B8', fontSize: 10 }}
                 stroke="#1E293B"/>
          <YAxis tick={{ fill: '#94A3B8', fontSize: 10 }}
                 stroke="#1E293B"/>
          <Tooltip content={<CustomTooltip/>}/>
          <Legend wrapperStyle={{ fontSize: '11px', color: '#94A3B8' }}/>

          <Line type="monotone" dataKey="total_wait" name="Total"
                stroke="#38BDF8" strokeWidth={2} dot={false}/>
          <Line type="monotone" dataKey="north" name="North"
                stroke="#22C55E" strokeWidth={1} dot={false}
                strokeDasharray="4 2"/>
          <Line type="monotone" dataKey="east" name="East"
                stroke="#EF4444" strokeWidth={1} dot={false}
                strokeDasharray="4 2"/>
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}