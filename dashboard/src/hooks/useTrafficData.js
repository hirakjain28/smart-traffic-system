// src/hooks/useTrafficData.js

/**
 * Master data hook — manages all traffic state for the dashboard.
 * 
 * This hook is the single source of truth.
 * Every component that needs traffic data gets it from here.
 * 
 * DATA FLOWS:
 * 1. On mount: fetch initial status + history from HTTP API
 * 2. WebSocket: update current state on every push from backend
 * 3. Every 5 seconds: re-fetch history for chart (WebSocket doesn't send history)
 * 4. On AI suggestion click: fetch latest suggestion
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  getTrafficStatus, getTrafficHistory,
  getAISuggestion, getDecisionLog, getTrafficSummary
} from '../services/api'
import { useWebSocket } from './useWebSocket'

// Initial empty state — prevents undefined errors before data loads
const INITIAL_STATE = {
  step:          0,
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

export function useTrafficData() {
  // Current live traffic state
  const [traffic,    setTraffic]    = useState(INITIAL_STATE)
  // Historical snapshots for the chart
  const [history,    setHistory]    = useState([])
  // AI suggestion data
  const [suggestion, setSuggestion] = useState(null)
  // Decision log entries
  const [decisions,  setDecisions]  = useState([])
  // Summary stats
  const [summary,    setSummary]    = useState(null)
  // Connection status
  const [connected,  setConnected]  = useState(false)

  const historyRef = useRef(history)
  historyRef.current = history

  // ── FETCH HISTORY (for chart) ──────────────────────────────────────────────
  const fetchHistory = useCallback(async () => {
    try {
      const data = await getTrafficHistory(60)
      if (data.snapshots) {
        // Reverse so oldest is first (chart reads left→right)
        setHistory([...data.snapshots].reverse())
      }
    } catch (e) { /* ignore */ }
  }, [])

  // ── FETCH AI SUGGESTION ────────────────────────────────────────────────────
  const fetchSuggestion = useCallback(async () => {
    try {
      const data = await getAISuggestion()
      setSuggestion(data)
    } catch (e) { /* ignore */ }
  }, [])

  // ── FETCH DECISION LOG ─────────────────────────────────────────────────────
  const fetchDecisions = useCallback(async () => {
    try {
      const data = await getDecisionLog(15)
      if (data.decisions) setDecisions(data.decisions)
    } catch (e) { /* ignore */ }
  }, [])

  // ── FETCH SUMMARY ──────────────────────────────────────────────────────────
  const fetchSummary = useCallback(async () => {
    try {
      const data = await getTrafficSummary()
      setSummary(data)
    } catch (e) { /* ignore */ }
  }, [])

  // ── WEBSOCKET HANDLER ──────────────────────────────────────────────────────
  // Called every time the backend pushes new data
  const handleWsMessage = useCallback((message) => {
    setConnected(true)

    if (message.type === 'initial_state' || message.data) {
      const raw = message.data || message

      // Extract traffic data from the nested structure
      const trafficData = raw.traffic || {}
      const newState = {
        step:          raw.step          ?? 0,
        phase:         raw.current_phase ?? 0,
        phase_name:    raw.phase_name    ?? 'Unknown',
        time_in_phase: raw.time_in_phase ?? 0,
        queue:         trafficData.queue    ?? INITIAL_STATE.queue,
        wait:          trafficData.wait     ?? INITIAL_STATE.wait,
        vehicles:      trafficData.vehicles ?? INITIAL_STATE.vehicles,
        total_wait:    Object.values(trafficData.wait    ?? {}).reduce((a,b)=>a+b,0),
        total_queue:   Object.values(trafficData.queue   ?? {}).reduce((a,b)=>a+b,0),
        last_action:   raw.last_action   ?? null,
        last_reward:   raw.last_reward   ?? 0,
        ai_mode:       raw.ai_mode       ?? true,
        is_running:    raw.is_running    ?? false,
      }
      setTraffic(newState)

      // Append new point to history for live chart
      const historyPoint = {
        step:       newState.step,
        total_wait: newState.total_wait,
        queue:      newState.queue,
        wait:       newState.wait,
        phase:      newState.phase,
      }
      setHistory(prev => {
        const updated = [...prev, historyPoint]
        // Keep last 60 points
        return updated.slice(-60)
      })
    }
  }, [])

  useWebSocket(handleWsMessage)

  // ── INITIAL DATA LOAD ──────────────────────────────────────────────────────
  useEffect(() => {
    // Fetch everything on mount
    const init = async () => {
      try {
        const status = await getTrafficStatus()
        setTraffic(prev => ({ ...prev, ...status }))
        setConnected(true)
      } catch (e) {
        setConnected(false)
      }
      fetchHistory()
      fetchSuggestion()
      fetchDecisions()
      fetchSummary()
    }
    init()

    // Refresh suggestion + decisions every 5 seconds
    const interval = setInterval(() => {
      fetchSuggestion()
      fetchDecisions()
      fetchSummary()
    }, 5000)

    return () => clearInterval(interval)
  }, [fetchHistory, fetchSuggestion, fetchDecisions, fetchSummary])

  // ── CONTROL FUNCTIONS (passed to components) ───────────────────────────────
  const refreshAll = useCallback(() => {
    fetchHistory()
    fetchSuggestion()
    fetchDecisions()
    fetchSummary()
  }, [fetchHistory, fetchSuggestion, fetchDecisions, fetchSummary])

  return {
    traffic,
    history,
    suggestion,
    decisions,
    summary,
    connected,
    refreshAll,
    setTraffic,  // for optimistic updates after override
  }
}