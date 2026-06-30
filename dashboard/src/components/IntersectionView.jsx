// src/components/IntersectionView.jsx

/**
 * India-style intersection view: only ONE approach is ever green.
 * Small numbered badges (1-4) show the fixed clockwise order —
 * the AI controls duration only, never the sequence.
 */

const PHASE_DIRECTION = {
  0: 'north', 1: 'north',
  2: 'east',  3: 'east',
  4: 'south', 5: 'south',
  6: 'west',  7: 'west',
}
const YELLOW_PHASES = new Set([1, 3, 5, 7])
const ROTATION_ORDER = { north: 1, east: 2, south: 3, west: 4 }

function colorFor(direction, phase) {
  if (PHASE_DIRECTION[phase] !== direction) return '#EF4444'
  return YELLOW_PHASES.has(phase) ? '#F59E0B' : '#22C55E'
}

export default function IntersectionView({ traffic }) {
  const phase = traffic.phase ?? 0
  const colors = {
    north: colorFor('north', phase),
    east:  colorFor('east',  phase),
    south: colorFor('south', phase),
    west:  colorFor('west',  phase),
  }

  const qN = Math.min(traffic.queue?.north ?? 0, 10)
  const qS = Math.min(traffic.queue?.south ?? 0, 10)
  const qE = Math.min(traffic.queue?.east  ?? 0, 10)
  const qW = Math.min(traffic.queue?.west  ?? 0, 10)

  return (
    <div className="bg-panel rounded-xl p-4 border border-elevated">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">Intersection View</h3>
        <span className="text-xs font-mono text-muted">
          Phase: <span className="text-accent">{traffic.phase_name}</span>
        </span>
      </div>

      <div className="flex justify-center">
        <svg viewBox="0 0 300 300" width="260" height="260">
          <rect x="120" y="0"   width="60" height="120" fill="#1E293B"/>
          <rect x="120" y="180" width="60" height="120" fill="#1E293B"/>
          <rect x="180" y="120" width="120" height="60" fill="#1E293B"/>
          <rect x="0"   y="120" width="120" height="60" fill="#1E293B"/>
          <rect x="120" y="120" width="60" height="60" fill="#1E293B"/>

          <line x1="150" y1="10" x2="150" y2="115" stroke="#334155" strokeWidth="1.5" strokeDasharray="8,6"/>
          <line x1="150" y1="185" x2="150" y2="290" stroke="#334155" strokeWidth="1.5" strokeDasharray="8,6"/>
          <line x1="185" y1="150" x2="290" y2="150" stroke="#334155" strokeWidth="1.5" strokeDasharray="8,6"/>
          <line x1="10" y1="150" x2="115" y2="150" stroke="#334155" strokeWidth="1.5" strokeDasharray="8,6"/>

          <rect x="120" y="0"   width="60" height="120" fill={colors.north} fillOpacity="0.08"/>
          <rect x="120" y="180" width="60" height="120" fill={colors.south} fillOpacity="0.08"/>
          <rect x="180" y="120" width="120" height="60" fill={colors.east}  fillOpacity="0.08"/>
          <rect x="0"   y="120" width="120" height="60" fill={colors.west}  fillOpacity="0.08"/>

          <circle cx="113" cy="115" r="5" fill={colors.north} style={{ filter: `drop-shadow(0 0 4px ${colors.north})` }}/>
          <circle cx="187" cy="185" r="5" fill={colors.south} style={{ filter: `drop-shadow(0 0 4px ${colors.south})` }}/>
          <circle cx="185" cy="113" r="5" fill={colors.east}  style={{ filter: `drop-shadow(0 0 4px ${colors.east})` }}/>
          <circle cx="115" cy="187" r="5" fill={colors.west}  style={{ filter: `drop-shadow(0 0 4px ${colors.west})` }}/>

          {/* Rotation order badges */}
          <circle cx="100" cy="103" r="7" fill="#0A0F1E" stroke={colors.north}/>
          <text x="100" y="106" textAnchor="middle" fill={colors.north} fontSize="8" fontFamily="JetBrains Mono">{ROTATION_ORDER.north}</text>
          <circle cx="197" cy="100" r="7" fill="#0A0F1E" stroke={colors.east}/>
          <text x="197" y="103" textAnchor="middle" fill={colors.east} fontSize="8" fontFamily="JetBrains Mono">{ROTATION_ORDER.east}</text>
          <circle cx="200" cy="197" r="7" fill="#0A0F1E" stroke={colors.south}/>
          <text x="200" y="200" textAnchor="middle" fill={colors.south} fontSize="8" fontFamily="JetBrains Mono">{ROTATION_ORDER.south}</text>
          <circle cx="103" cy="200" r="7" fill="#0A0F1E" stroke={colors.west}/>
          <text x="103" y="203" textAnchor="middle" fill={colors.west} fontSize="8" fontFamily="JetBrains Mono">{ROTATION_ORDER.west}</text>

          {Array.from({ length: qN }, (_, i) => <rect key={`qn${i}`} x="128" y={108 - i * 9} width="10" height="6" rx="2" fill="#38BDF8" fillOpacity="0.7"/>)}
          {Array.from({ length: qS }, (_, i) => <rect key={`qs${i}`} x="162" y={186 + i * 9} width="10" height="6" rx="2" fill="#38BDF8" fillOpacity="0.7"/>)}
          {Array.from({ length: qE }, (_, i) => <rect key={`qe${i}`} x={186 + i * 9} y="128" width="6" height="10" rx="2" fill="#38BDF8" fillOpacity="0.7"/>)}
          {Array.from({ length: qW }, (_, i) => <rect key={`qw${i}`} x={108 - i * 9} y="162" width="6" height="10" rx="2" fill="#38BDF8" fillOpacity="0.7"/>)}

          <text x="150" y="14"  textAnchor="middle" fill="#94A3B8" fontSize="11" fontFamily="JetBrains Mono">N</text>
          <text x="150" y="296" textAnchor="middle" fill="#94A3B8" fontSize="11" fontFamily="JetBrains Mono">S</text>
          <text x="291" y="153" textAnchor="middle" fill="#94A3B8" fontSize="11" fontFamily="JetBrains Mono">E</text>
          <text x="9"   y="153" textAnchor="middle" fill="#94A3B8" fontSize="11" fontFamily="JetBrains Mono">W</text>
          <text x="150" y="147" textAnchor="middle" fill="#94A3B8" fontSize="8" fontFamily="JetBrains Mono">t={traffic.time_in_phase ?? 0}s</text>
        </svg>
      </div>

      <p className="text-xs text-muted mt-2 text-center">
        Clockwise rotation — one direction at a time (N→E→S→W)
      </p>
    </div>
  )
}