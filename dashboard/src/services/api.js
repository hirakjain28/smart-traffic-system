// src/services/api.js

/**
 * All API calls to the FastAPI backend.
 * 
 * We use axios for HTTP requests.
 * All functions return promises — components use them with async/await.
 * 
 * BASE_URL points to our FastAPI backend.
 * Change this if you deploy the backend to a server.
 */

import axios from 'axios'

const BASE_URL = 'http://localhost:8000'

// Create axios instance with default config
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 5000,  // 5 second timeout
})

// ── TRAFFIC ENDPOINTS ──────────────────────────────────────────────────────────

/** Get current live traffic state */
export const getTrafficStatus = () =>
  api.get('/api/traffic/status').then(r => r.data)

/** Get last N traffic snapshots for charts */
export const getTrafficHistory = (limit = 60) =>
  api.get(`/api/traffic/history?limit=${limit}`).then(r => r.data)

/** Get aggregate traffic statistics */
export const getTrafficSummary = () =>
  api.get('/api/traffic/summary').then(r => r.data)

// ── SIGNAL ENDPOINTS ──────────────────────────────────────────────────────────

/** Get current signal phase state */
export const getSignalState = () =>
  api.get('/api/signals/state').then(r => r.data)

// ── AI ENDPOINTS ──────────────────────────────────────────────────────────────

/** Get AI's current recommendation */
export const getAISuggestion = () =>
  api.get('/api/logs/ai/suggestion').then(r => r.data)

/** Get recent AI decision history */
export const getDecisionLog = (limit = 15) =>
  api.get(`/api/logs/decisions?limit=${limit}`).then(r => r.data)

// ── OVERRIDE ENDPOINTS ────────────────────────────────────────────────────────

/**
 * Force a specific traffic light phase.
 * @param {number} phase - 0=NS Green, 2=EW Green
 * @param {number} duration - seconds to hold (optional)
 * @param {string} reason - operator reason (optional)
 */
export const overridePhase = (phase, duration = null, reason = null) =>
  api.post('/api/override/phase', { phase, duration, reason }).then(r => r.data)

/**
 * Toggle AI mode on/off.
 * @param {boolean} aiMode - true=AI controls, false=Manual
 */
export const setControlMode = (aiMode) =>
  api.post(`/api/override/mode?ai_mode=${aiMode}`).then(r => r.data)

/** Get history of manual overrides */
export const getOverrideHistory = () =>
  api.get('/api/override/history').then(r => r.data)