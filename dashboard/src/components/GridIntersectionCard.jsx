// src/components/GridIntersectionCard.jsx
export default function GridIntersectionCard({ label, data }) {
  const t = data.traffic || {}
  const q = t.queue || {}
  const w = t.wait || {}

  return (
    <div className="bg-panel rounded-xl p-3 border border-elevated">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-bold text-accent">Junction {label}</span>
        <span className="text-xs font-mono text-sgreen">{data.phase_name}</span>
      </div>
      <div className="grid grid-cols-4 gap-1 text-center">
        {['north', 'east', 'south', 'west'].map(dir => (
          <div key={dir} className="bg-elevated rounded p-1.5">
            <p className="text-[10px] text-muted uppercase">{dir.slice(0,1)}</p>
            <p className="text-sm font-mono text-white">{q[dir] ?? 0}</p>
            <p className="text-[10px] text-muted">{Math.round(w[dir] ?? 0)}s</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted mt-2">
        Total wait: <span className="font-mono text-white">{Math.round(t.total_wait ?? 0)}s</span>
      </p>
    </div>
  )
}