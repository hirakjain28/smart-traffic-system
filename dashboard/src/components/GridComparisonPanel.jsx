// src/components/GridComparisonPanel.jsx
export default function GridComparisonPanel({ comparison }) {
  const { cumulative_adaptive_wait, cumulative_fixed_wait, improvement_pct } = comparison
  const maxBar = Math.max(cumulative_fixed_wait, cumulative_adaptive_wait, 1)

  return (
    <div className="bg-panel rounded-xl p-4 border border-elevated">
      <h3 className="text-sm font-semibold text-white mb-1">
        Live Comparison — Fixed vs Adaptive
      </h3>
      <p className="text-xs text-muted mb-4">
        Same live traffic, two timing strategies, running total wait
      </p>

      <div className="space-y-3">
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-muted">Fixed 30s Timer (estimated)</span>
            <span className="font-mono text-sred">
              {Math.round(cumulative_fixed_wait).toLocaleString()}s
            </span>
          </div>
          <div className="h-3 bg-elevated rounded-full overflow-hidden">
            <div className="h-full bg-sred/70 rounded-full"
                 style={{ width: `${(cumulative_fixed_wait / maxBar) * 100}%` }}/>
          </div>
        </div>

        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-muted">Pressure-Adaptive (actual)</span>
            <span className="font-mono text-sgreen">
              {Math.round(cumulative_adaptive_wait).toLocaleString()}s
            </span>
          </div>
          <div className="h-3 bg-elevated rounded-full overflow-hidden">
            <div className="h-full bg-sgreen/80 rounded-full transition-all duration-700"
                 style={{ width: `${(cumulative_adaptive_wait / maxBar) * 100}%` }}/>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-elevated text-center">
        <p className="text-xs text-muted mb-1">System-wide improvement so far</p>
        <p className={`text-3xl font-bold font-mono ${
          improvement_pct > 0 ? 'text-sgreen' : 'text-muted'
        }`}>
          {improvement_pct > 0 ? '+' : ''}{improvement_pct}%
        </p>
      </div>
    </div>
  )
}