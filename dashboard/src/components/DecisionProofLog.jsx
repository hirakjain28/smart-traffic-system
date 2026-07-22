// src/components/DecisionProofLog.jsx
export default function DecisionProofLog({ decisionLog }) {
  if (!decisionLog?.length) {
    return (
      <div className="bg-panel rounded-xl p-4 border border-elevated">
        <h3 className="text-sm font-semibold text-white mb-2">Timing Decisions — Live Proof</h3>
        <p className="text-muted text-xs">Waiting for the first decision...</p>
      </div>
    )
  }

  return (
    <div className="bg-panel rounded-xl p-4 border border-elevated">
      <h3 className="text-sm font-semibold text-white mb-1">Timing Decisions — Live Proof</h3>
      <p className="text-xs text-muted mb-3">
        Every switch, with the exact traffic pressure that triggered it
      </p>

      <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
        {decisionLog.map((d, i) => (
          <div key={i} className="text-xs border-b border-elevated pb-2 last:border-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono px-1.5 py-0.5 rounded bg-accent/10 text-accent">
                {d.intersection}
              </span>
              <span className="text-white font-semibold">{d.direction}</span>
              <span className="text-muted">held</span>
              <span className="font-mono text-samber">{d.held_seconds}s</span>
              <span className="text-muted ml-auto">{d.time}</span>
            </div>
            <p className="text-muted">
              Switched because next direction's pressure
              (<span className="font-mono text-sgreen">{d.next_pressure}</span>)
              exceeded current
              (<span className="font-mono text-sred">{d.current_pressure}</span>)
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}