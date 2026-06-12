// src/components/IntersectionView.jsx

/**
 * Live SVG diagram of the intersection.
 * 
 * Shows a top-down bird's-eye view of the 4-way intersection
 * with animated traffic light colors that change in real time.
 * 
 * The signal light colors update as SUMO runs:
 * - North/South green  → those arms glow green
 * - East/West green    → those arms glow green  
 * - Yellow transition  → amber glow
 */

const PHASE_COLORS = {
  0: { ns: '#22C55E', ew: '#EF4444' },  // NS Green, EW Red
  1: { ns: '#F59E0B', ew: '#EF4444' },  // NS Yellow, EW Red
  2: { ns: '#EF4444', ew: '#22C55E' },  // NS Red, EW Green
  3: { ns: '#EF4444', ew: '#F59E0B' },  // NS Red, EW Yellow
}

export default function IntersectionView({ traffic }) {
  const phase    = traffic.phase ?? 0
  const colors   = PHASE_COLORS[phase] || PHASE_COLORS[0]

  // Queue lengths for visual density
  const qN = Math.min(traffic.queue?.north ?? 0, 10)
  const qS = Math.min(traffic.queue?.south ?? 0, 10)
  const qE = Math.min(traffic.queue?.east  ?? 0, 10)
  const qW = Math.min(traffic.queue?.west  ?? 0, 10)

  return (
    <div className="bg-panel rounded-xl p-4 border border-elevated">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">
          Intersection View
        </h3>
        <span className="text-xs font-mono text-muted">
          Phase: <span className="text-accent">{traffic.phase_name}</span>
        </span>
      </div>

      <div className="flex justify-center">
        <svg viewBox="0 0 300 300" width="260" height="260">

          {/* ── ROAD NETWORK ──────────────────────────────────────── */}

          {/* Road background (dark asphalt) */}
          {/* North arm */}
          <rect x="120" y="0"   width="60" height="120" fill="#1E293B"/>
          {/* South arm */}
          <rect x="120" y="180" width="60" height="120" fill="#1E293B"/>
          {/* East arm */}
          <rect x="180" y="120" width="120" height="60" fill="#1E293B"/>
          {/* West arm */}
          <rect x="0"   y="120" width="120" height="60" fill="#1E293B"/>
          {/* Center box */}
          <rect x="120" y="120" width="60" height="60" fill="#1E293B"/>

          {/* Road lane markings (dashed white center lines) */}
          {/* North lane divider */}
          <line x1="150" y1="10" x2="150" y2="115"
                stroke="#334155" strokeWidth="1.5" strokeDasharray="8,6"/>
          {/* South lane divider */}
          <line x1="150" y1="185" x2="150" y2="290"
                stroke="#334155" strokeWidth="1.5" strokeDasharray="8,6"/>
          {/* East lane divider */}
          <line x1="185" y1="150" x2="290" y2="150"
                stroke="#334155" strokeWidth="1.5" strokeDasharray="8,6"/>
          {/* West lane divider */}
          <line x1="10" y1="150" x2="115" y2="150"
                stroke="#334155" strokeWidth="1.5" strokeDasharray="8,6"/>

          {/* ── SIGNAL GLOW OVERLAYS ───────────────────────────────── */}

          {/* North signal glow */}
          <rect x="120" y="0" width="60" height="120"
                fill={colors.ns} fillOpacity="0.08"/>
          {/* South signal glow */}
          <rect x="120" y="180" width="60" height="120"
                fill={colors.ns} fillOpacity="0.08"/>
          {/* East signal glow */}
          <rect x="180" y="120" width="120" height="60"
                fill={colors.ew} fillOpacity="0.08"/>
          {/* West signal glow */}
          <rect x="0" y="120" width="120" height="60"
                fill={colors.ew} fillOpacity="0.08"/>

          {/* ── TRAFFIC LIGHT SIGNALS ─────────────────────────────── */}

          {/* North signal light */}
          <circle cx="113" cy="115" r="5" fill={colors.ns}
                  style={{ filter: `drop-shadow(0 0 4px ${colors.ns})` }}/>
          {/* South signal light */}
          <circle cx="187" cy="185" r="5" fill={colors.ns}
                  style={{ filter: `drop-shadow(0 0 4px ${colors.ns})` }}/>
          {/* East signal light */}
          <circle cx="185" cy="113" r="5" fill={colors.ew}
                  style={{ filter: `drop-shadow(0 0 4px ${colors.ew})` }}/>
          {/* West signal light */}
          <circle cx="115" cy="187" r="5" fill={colors.ew}
                  style={{ filter: `drop-shadow(0 0 4px ${colors.ew})` }}/>

          {/* ── QUEUE DENSITY INDICATORS ──────────────────────────── */}

          {/* North queue dots */}
          {Array.from({ length: qN }, (_, i) => (
            <rect key={`qn${i}`}
              x="128" y={108 - i * 9} width="10" height="6"
              rx="2" fill="#38BDF8" fillOpacity="0.7"/>
          ))}
          {/* South queue dots */}
          {Array.from({ length: qS }, (_, i) => (
            <rect key={`qs${i}`}
              x="162" y={186 + i * 9} width="10" height="6"
              rx="2" fill="#38BDF8" fillOpacity="0.7"/>
          ))}
          {/* East queue dots */}
          {Array.from({ length: qE }, (_, i) => (
            <rect key={`qe${i}`}
              x={186 + i * 9} y="128" width="6" height="10"
              rx="2" fill="#38BDF8" fillOpacity="0.7"/>
          ))}
          {/* West queue dots */}
          {Array.from({ length: qW }, (_, i) => (
            <rect key={`qw${i}`}
              x={108 - i * 9} y="162" width="6" height="10"
              rx="2" fill="#38BDF8" fillOpacity="0.7"/>
          ))}

          {/* ── DIRECTION LABELS ──────────────────────────────────── */}
          <text x="150" y="14"  textAnchor="middle" fill="#94A3B8"
                fontSize="11" fontFamily="JetBrains Mono">N</text>
          <text x="150" y="296" textAnchor="middle" fill="#94A3B8"
                fontSize="11" fontFamily="JetBrains Mono">S</text>
          <text x="291" y="153" textAnchor="middle" fill="#94A3B8"
                fontSize="11" fontFamily="JetBrains Mono">E</text>
          <text x="9"   y="153" textAnchor="middle" fill="#94A3B8"
                fontSize="11" fontFamily="JetBrains Mono">W</text>

          {/* ── QUEUE COUNT LABELS ────────────────────────────────── */}
          {qN > 0 && <text x="150" y={100 - qN * 9}
            textAnchor="middle" fill="#38BDF8" fontSize="9"
            fontFamily="JetBrains Mono">{qN}</text>}
          {qS > 0 && <text x="150" y={195 + qS * 9}
            textAnchor="middle" fill="#38BDF8" fontSize="9"
            fontFamily="JetBrains Mono">{qS}</text>}
          {qE > 0 && <text x={192 + qE * 9} y="148"
            fill="#38BDF8" fontSize="9"
            fontFamily="JetBrains Mono">{qE}</text>}
          {qW > 0 && <text x={100 - qW * 9} y="148"
            fill="#38BDF8" fontSize="9"
            fontFamily="JetBrains Mono">{qW}</text>}

          {/* ── CENTER STEP COUNTER ───────────────────────────────── */}
          <text x="150" y="147" textAnchor="middle" fill="#94A3B8"
                fontSize="8" fontFamily="JetBrains Mono">
            t={traffic.time_in_phase ?? 0}s
          </text>

        </svg>
      </div>
    </div>
  )
}