// src/components/DecisionLog.jsx

/**
 * Scrollable log of recent AI decisions.
 */

const PHASE_NAMES = {
  0: 'NS Green', 1: 'NS Yellow', 2: 'EW Green', 3: 'EW Yellow'
}

export default function DecisionLog({ decisions }) {
  if (!decisions?.length) {
    return (
      <div className="bg-panel rounded-xl p-4 border border-elevated">
        <h3 className="text-sm font-semibold text-white mb-2">Decision Log</h3>
        <p className="text-muted text-xs">No decisions logged yet...</p>
      </div>
    )
  }

  return (
    <div className="bg-panel rounded-xl p-4 border border-elevated">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">Decision Log</h3>
        <span className="text-xs text-muted">{decisions.length} entries</span>
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
        {decisions.map((d, i) => (
          <div key={i}
               className="flex items-start gap-3 text-xs border-b
                          border-elevated pb-2 last:border-0">

            {/* Action badge */}
            <span className={`font-mono px-1.5 py-0.5 rounded text-xs shrink-0 ${
              d.action === 'SWITCH'
                ? 'bg-sgreen/10 text-sgreen'
                : d.overridden
                ? 'bg-samber/10 text-samber'
                : 'bg-accent/10 text-accent'
            }`}>
              {d.overridden ? 'FORCED' : d.action}
            </span>

            {/* Details */}
            <div className="flex-1 min-w-0">
              <div className="text-muted truncate">
                Wait: <span className="text-white font-mono">
                  {Math.round(d.total_wait ?? 0)}s
                </span>
                {' · '}
                Reward: <span className={`font-mono ${
                  (d.reward ?? 0) > 0 ? 'text-sgreen' : 'text-sred'
                }`}>
                  {(d.reward ?? 0).toFixed(1)}
                </span>
              </div>
              <div className="text-muted/60 text-xs mt-0.5">
                Step {d.step} ·{' '}
                {d.ai_mode ? '🤖 AI' : '👤 Manual'}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}