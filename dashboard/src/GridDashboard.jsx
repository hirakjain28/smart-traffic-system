// src/GridDashboard.jsx
import { useGridData } from './hooks/useGridData'
import GridIntersectionCard from './components/GridIntersectionCard'
import GridComparisonPanel from './components/GridComparisonPanel'
import DecisionProofLog from './components/DecisionProofLog'

export default function GridDashboard() {
  const { intersections, comparison, decisionLog, connected } = useGridData()

  return (
    <div className="min-h-screen bg-navy p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-white font-semibold">2×2 Grid — Multi-Intersection Control</h1>
          <p className="text-muted text-xs">Pressure-based adaptive timing, live</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-sgreen animate-pulse' : 'bg-sred'}`}/>
          <span className="text-xs text-muted font-mono">{connected ? 'LIVE' : 'OFFLINE'}</span>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-7">
          {/* 2x2 physical layout matching the real grid */}
          <div className="grid grid-cols-2 gap-4">
            <GridIntersectionCard label="A" data={intersections.A}/>
            <GridIntersectionCard label="B" data={intersections.B}/>
            <GridIntersectionCard label="C" data={intersections.C}/>
            <GridIntersectionCard label="D" data={intersections.D}/>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-5 space-y-4">
          <GridComparisonPanel comparison={comparison}/>
          <DecisionProofLog decisionLog={decisionLog}/>
        </div>
      </div>
    </div>
  )
}