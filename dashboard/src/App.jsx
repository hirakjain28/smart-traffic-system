// src/App.jsx

/**
 * Main dashboard layout.
 * 
 * LAYOUT (3-column on desktop):
 * 
 * ┌─────────────────────────────────────────────────────────┐
 * │                      HEADER                             │
 * ├──────────────┬──────────────────────────┬───────────────┤
 * │              │   N Signal Card          │               │
 * │ Intersection │ W Signal Card E Signal   │ AI Suggestion │
 * │   SVG View   │   S Signal Card          │               │
 * │              ├──────────────────────────┤ Override      │
 * │              │   Traffic Chart          │ Panel         │
 * ├──────────────┴──────────────────────────┤               │
 * │           Decision Log                  │ Decision Log  │
 * └─────────────────────────────────────────┴───────────────┘
 */

import { useTrafficData } from './hooks/useTrafficData'
import Header           from './components/Header'
import SignalCard       from './components/SignalCard'
import IntersectionView from './components/IntersectionView'
import TrafficChart     from './components/TrafficChart'
import AISuggestion     from './components/AISuggestion'
import OverridePanel    from './components/OverridePanel'
import DecisionLog      from './components/DecisionLog'

export default function App() {
  const {
    traffic, history, suggestion,
    decisions, summary, connected,
    refreshAll, setTraffic
  } = useTrafficData()

  const handleModeChange = (newMode) => {
    setTraffic(prev => ({ ...prev, ai_mode: newMode }))
  }

  return (
    <div className="min-h-screen bg-navy flex flex-col">

      {/* ── HEADER ──────────────────────────────────────────────── */}
      <Header
        traffic={traffic}
        connected={connected}
        onModeChange={handleModeChange}
      />

      {/* ── MAIN CONTENT ────────────────────────────────────────── */}
      <main className="flex-1 p-4 grid grid-cols-12 gap-4 max-w-screen-2xl mx-auto w-full">

        {/* ── LEFT COLUMN: Intersection view + summary ──────────── */}
        <div className="col-span-12 lg:col-span-3 space-y-4">

          {/* Live intersection SVG */}
          <IntersectionView traffic={traffic}/>

          {/* Summary stats */}
          <div className="bg-panel rounded-xl p-4 border border-elevated">
            <h3 className="text-xs text-muted uppercase tracking-wider mb-3">
              Session Stats
            </h3>
            <div className="space-y-2">
              {[
                { label: 'Avg Wait',   value: `${summary?.avg_wait ?? 0}s`,
                  color: 'text-white' },
                { label: 'Max Wait',   value: `${summary?.max_wait ?? 0}s`,
                  color: 'text-sred' },
                { label: 'Avg Queue',  value: summary?.avg_queue ?? 0,
                  color: 'text-white' },
                { label: 'Snapshots', value: summary?.total_snapshots ?? 0,
                  color: 'text-accent' },
              ].map(s => (
                <div key={s.label}
                     className="flex justify-between items-center">
                  <span className="text-xs text-muted">{s.label}</span>
                  <span className={`text-xs font-mono ${s.color}`}>
                    {s.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── CENTER COLUMN: Signal cards + chart ───────────────── */}
        <div className="col-span-12 lg:col-span-6 space-y-4">

          {/* Signal cards — 2x2 grid matching intersection layout */}
          <div>
            {/* North card — centered */}
            <div className="grid grid-cols-3 gap-3 mb-3">
              <div/>
              <SignalCard direction="north" traffic={traffic}/>
              <div/>
            </div>
            {/* West + East cards */}
            <div className="grid grid-cols-2 gap-3 mb-3">
              <SignalCard direction="west" traffic={traffic}/>
              <SignalCard direction="east" traffic={traffic}/>
            </div>
            {/* South card — centered */}
            <div className="grid grid-cols-3 gap-3">
              <div/>
              <SignalCard direction="south" traffic={traffic}/>
              <div/>
            </div>
          </div>

          {/* Live traffic chart */}
          <TrafficChart history={history}/>

          {/* Current phase info bar */}
          <div className="bg-panel rounded-xl px-4 py-3 border border-elevated
                          flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${
                traffic.phase === 0 || traffic.phase === 2
                  ? 'bg-sgreen signal-green'
                  : 'bg-samber signal-amber'
              }`}/>
              <span className="text-sm font-semibold text-white">
                {traffic.phase_name}
              </span>
              <span className="text-xs text-muted font-mono">
                for {Math.round(traffic.time_in_phase)}s
              </span>
            </div>
            <div className="flex items-center gap-4 text-xs font-mono">
              <span className="text-muted">
                Action: <span className={`${
                  traffic.last_action === 'SWITCH'
                    ? 'text-sgreen'
                    : traffic.last_action === 'OVERRIDE'
                    ? 'text-samber'
                    : 'text-accent'
                }`}>{traffic.last_action ?? '—'}</span>
              </span>
              <span className="text-muted">
                Reward: <span className={`${
                  (traffic.last_reward ?? 0) > 0
                    ? 'text-sgreen' : 'text-sred'
                }`}>{(traffic.last_reward ?? 0).toFixed(2)}</span>
              </span>
            </div>
          </div>
        </div>

        {/* ── RIGHT COLUMN: AI + controls + log ─────────────────── */}
        <div className="col-span-12 lg:col-span-3 space-y-4">

          <AISuggestion
            suggestion={suggestion}
            aiMode={traffic.ai_mode}
          />

          <OverridePanel onOverride={refreshAll}/>

          <DecisionLog decisions={decisions}/>

        </div>
      </main>
    </div>
  )
}