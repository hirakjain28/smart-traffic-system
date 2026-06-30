// src/hooks/useTrafficData.js

/**
 * BUGFIXES IN THIS VERSION:
 *  1. The live chart no longer gets seeded from the database on mount.
 *     Before, a slow DB fetch could resolve AFTER a few WebSocket
 *     messages had already arrived, and silently overwrite/scramble
 *     the chart's data. Now the WebSocket is the single source of
 *     truth for the live chart — no race possible.
 *  2. The AI suggestion is now read directly from the WebSocket
 *     payload (which the backend already includes, perfectly in sync
 *     with the traffic numbers) instead of a separate 5-second HTTP
 *     poll that could show stale numbers.
 *  3. `step` now reflects the backend's global, never-resetting
 *     counter, so the chart and header can never jump backwards.
 */

import { useState, useEffect, useCallback } from 'react'
import {
  getTrafficStatus, getAISuggestion,
  getDecisionLog, getTrafficSummary
} from '../services/api'
import { useWebSocket } from './useWebSocket'

const INITIAL_STATE = {
  step:          0,
  episode:       0,
  phase:         0,
  phase_name:    'Loading...',
  time_in_phase: 0,
  queue:         { north: 0, south: 0, east: 0, west: 0 },
  wait:          { north: 0, south: 0, east: 0, west: 0 },
  vehicles:      { north: 0, south: 0, east: 0, west: 0 },
  total_wait:    0,
  total_queue:   0,
  last_action:   null,
  last_reward:   0,
  ai_mode:       true,
  is_running:    false,
}

const MAX_CHART_POINTS = 60

export function useTrafficData() {
  const [traffic,    setTraffic]    = useState(INITIAL_STATE)
  const [history,    setHistory]    = useState([])   // live chart — WS-only now
  const [suggestion, setSuggestion] = useState(null)
  const [decisions,  setDecisions]  = useState([])
  const [summary,    setSummary]    = useState(null)
  const [connected,  setConnected]  = useState(false)

  const fetchSuggestion = useCallback(async () => {
    try { setSuggestion(await getAISuggestion()) } catch { /* ignore */ }
  }, [])

  const fetchDecisions = useCallback(async () => {
    try {
      const data = await getDecisionLog(15)
      if (data.decisions) setDecisions(data.decisions)
    } catch { /* ignore */ }
  }, [])

  const fetchSummary = useCallback(async () => {
    try { setSummary(await getTrafficSummary()) } catch { /* ignore */ }
  }, [])

  // ── WEBSOCKET HANDLER ──────────────────────────────────────────────────────
  const handleWsMessage = useCallback((message) => {
    setConnected(true)
    const raw = message.data || message
    const trafficData = raw.traffic || {}

    const newState = {
      step:          raw.step          ?? 0,   // this is the GLOBAL counter now
      episode:       raw.episode        ?? 0,
      phase:         raw.current_phase ?? 0,
      phase_name:    raw.phase_name    ?? 'Unknown',
      time_in_phase: raw.time_in_phase ?? 0,
      queue:         trafficData.queue    ?? INITIAL_STATE.queue,
      wait:          trafficData.wait     ?? INITIAL_STATE.wait,
      vehicles:      trafficData.vehicles ?? INITIAL_STATE.vehicles,
      total_wait:    Object.values(trafficData.wait  ?? {}).reduce((a, b) => a + b, 0),
      total_queue:   Object.values(trafficData.queue ?? {}).reduce((a, b) => a + b, 0),
      last_action:   raw.last_action   ?? null,
      last_reward:   raw.last_reward   ?? 0,
      ai_mode:       raw.ai_mode       ?? true,
      is_running:    raw.is_running    ?? false,
    }
    setTraffic(newState)

    // AI suggestion comes straight off this same payload — always in sync
    if (raw.ai_suggestion) setSuggestion(raw.ai_suggestion)

    // Append to the live chart (single source of truth — no DB merge)
    setHistory(prev => {
      const point = {
        step:       newState.step,
        total_wait: newState.total_wait,
        wait:       newState.wait,
      }
      const updated = [...prev, point]
      return updated.slice(-MAX_CHART_POINTS)
    })
  }, [])

  useWebSocket(handleWsMessage)

  // ── INITIAL LOAD (status + suggestion/decisions/summary, NOT chart history) ─
  useEffect(() => {
    const init = async () => {
      try {
        const status = await getTrafficStatus()
        setTraffic(prev => ({ ...prev, ...status }))
        setConnected(true)
      } catch {
        setConnected(false)
      }
      fetchSuggestion()
      fetchDecisions()
      fetchSummary()
    }
    init()

    const interval = setInterval(() => {
      fetchDecisions()
      fetchSummary()
    }, 5000)

    return () => clearInterval(interval)
  }, [fetchSuggestion, fetchDecisions, fetchSummary])

  const refreshAll = useCallback(() => {
    fetchSuggestion()
    fetchDecisions()
    fetchSummary()
  }, [fetchSuggestion, fetchDecisions, fetchSummary])

  return {
    traffic, history, suggestion, decisions, summary,
    connected, refreshAll, setTraffic,
  }
}