// src/components/SignalCard.jsx

/**
 * One card showing traffic data for one direction (N/S/E/W).
 * 
 * Shows:
 * - Direction name and arrow
 * - Green/Red status based on current phase
 * - Queue length (cars stopped)
 * - Wait time (seconds)
 * - Vehicle count
 * - Visual severity bar
 */

const DIRECTION_ARROWS = {
  north: '↑', south: '↓', east: '→', west: '←'
}

// Which directions have green light for each phase
const GREEN_DIRECTIONS = {
  0: ['north', 'south'],  // Phase 0: NS Green
  1: ['north', 'south'],  // Phase 1: NS Yellow (still show as green-ish)
  2: ['east',  'west'],   // Phase 2: EW Green
  3: ['east',  'west'],   // Phase 3: EW Yellow
}

const YELLOW_PHASES = [1, 3]

export default function SignalCard({ direction, traffic }) {
  const queue    = traffic.queue?.[direction]    ?? 0
  const wait     = traffic.wait?.[direction]     ?? 0
  const vehicles = traffic.vehicles?.[direction] ?? 0
  const phase    = traffic.phase ?? 0

  // Determine signal state for this direction
  const greenDirs   = GREEN_DIRECTIONS[phase] || []
  const isGreen     = greenDirs.includes(direction)
  const isYellow    = YELLOW_PHASES.includes(phase) && greenDirs.includes(direction)

  // Severity: how bad is the wait time?
  // 0-50s = low, 50-150s = medium, 150+ = high
  const severity = wait > 150 ? 'high' : wait > 50 ? 'medium' : 'low'
  const severityPct = Math.min((wait / 300) * 100, 100)

  const severityColor = {
    low:    'bg-sgreen',
    medium: 'bg-samber',
    high:   'bg-sred',
  }[severity]

  const signalColor = isYellow
    ? 'border-samber text-samber signal-amber'
    : isGreen
    ? 'border-sgreen text-sgreen signal-green'
    : 'border-sred   text-sred   signal-red'

  return (
    <div className={`bg-panel rounded-xl p-4 border transition-all duration-500 ${
      isGreen && !isYellow
        ? 'border-sgreen/40'
        : isYellow
        ? 'border-samber/40'
        : 'border-sred/20'
    }`}>

      {/* Direction header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">{DIRECTION_ARROWS[direction]}</span>
          <span className="text-sm font-semibold text-white uppercase tracking-wider">
            {direction}
          </span>
        </div>

        {/* Signal light indicator */}
        <div className={`w-4 h-4 rounded-full border-2 ${signalColor}`}/>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <p className="text-xs text-muted mb-1">Queue</p>
          <p className={`data-num text-2xl ${
            queue > 10 ? 'text-sred' : queue > 5 ? 'text-samber' : 'text-white'
          }`}>
            {queue}
          </p>
          <p className="text-xs text-muted">cars</p>
        </div>
        <div>
          <p className="text-xs text-muted mb-1">Wait</p>
          <p className={`data-num text-2xl ${
            wait > 150 ? 'text-sred' : wait > 50 ? 'text-samber' : 'text-white'
          }`}>
            {wait > 999 ? `${(wait/1000).toFixed(1)}k` : Math.round(wait)}
          </p>
          <p className="text-xs text-muted">seconds</p>
        </div>
      </div>

      {/* Vehicle count */}
      <p className="text-xs text-muted mb-2">
        {vehicles} vehicles on road
      </p>

      {/* Severity bar */}
      <div className="h-1.5 bg-elevated rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${severityColor}`}
          style={{ width: `${severityPct}%` }}
        />
      </div>
    </div>
  )
}