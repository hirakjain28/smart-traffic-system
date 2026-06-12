// src/components/AISuggestion.jsx

/**
 * Shows what the AI currently recommends.
 * Visible even in Manual mode so operators can see AI's opinion.
 */

export default function AISuggestion({ suggestion, aiMode }) {
  if (!suggestion) {
    return (
      <div className="bg-panel rounded-xl p-4 border border-elevated">
        <h3 className="text-sm font-semibold text-white mb-2">AI Recommendation</h3>
        <p className="text-muted text-xs">Loading suggestion...</p>
      </div>
    )
  }

  const isSwitch     = suggestion.action === 'SWITCH'
  const confidence   = Math.round((suggestion.confidence ?? 0) * 100)
  const confColor    = confidence > 70 ? 'text-sgreen'
                     : confidence > 40 ? 'text-samber'
                     : 'text-sred'

  // Q-values
  const qKeep   = suggestion.q_values?.keep   ?? 0
  const qSwitch = suggestion.q_values?.switch ?? 0
  const qMax    = Math.max(Math.abs(qKeep), Math.abs(qSwitch), 1)

  return (
    <div className={`bg-panel rounded-xl p-4 border transition-colors ${
      aiMode ? 'border-accent/30' : 'border-elevated'
    }`}>

      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">AI Recommendation</h3>
        {!aiMode && (
          <span className="text-xs text-samber font-mono bg-samber/10
                           px-2 py-0.5 rounded">MANUAL MODE</span>
        )}
      </div>

      {/* Main recommendation */}
      <div className={`rounded-lg p-3 mb-3 ${
        isSwitch ? 'bg-sgreen/10 border border-sgreen/20'
                 : 'bg-accent/10 border border-accent/20'
      }`}>
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-lg font-bold font-mono ${
            isSwitch ? 'text-sgreen' : 'text-accent'
          }`}>
            {suggestion.action}
          </span>
          <span className={`text-xs font-mono ${confColor}`}>
            {confidence}% confident
          </span>
        </div>
        <p className="text-xs text-muted">{suggestion.reason}</p>
      </div>

      {/* Q-value bars */}
      <div className="space-y-2">
        <p className="text-xs text-muted mb-2">Q-values (higher = better)</p>

        {/* KEEP bar */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-muted font-mono">KEEP</span>
            <span className={`font-mono ${
              qKeep >= qSwitch ? 'text-accent' : 'text-muted'
            }`}>{qKeep.toFixed(2)}</span>
          </div>
          <div className="h-1.5 bg-elevated rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                qKeep >= qSwitch ? 'bg-accent' : 'bg-elevated'
              }`}
              style={{
                width: `${Math.max((Math.abs(qKeep) / qMax) * 100, 2)}%`
              }}
            />
          </div>
        </div>

        {/* SWITCH bar */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-muted font-mono">SWITCH</span>
            <span className={`font-mono ${
              qSwitch > qKeep ? 'text-sgreen' : 'text-muted'
            }`}>{qSwitch.toFixed(2)}</span>
          </div>
          <div className="h-1.5 bg-elevated rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                qSwitch > qKeep ? 'bg-sgreen' : 'bg-elevated'
              }`}
              style={{
                width: `${Math.max((Math.abs(qSwitch) / qMax) * 100, 2)}%`
              }}
            />
          </div>
        </div>
      </div>

      {/* Total wait */}
      <div className="mt-3 pt-3 border-t border-elevated">
        <p className="text-xs text-muted">
          Current total wait:
          <span className="font-mono text-white ml-1">
            {Math.round(suggestion.total_wait ?? 0)}s
          </span>
        </p>
      </div>
    </div>
  )
}