# 🚦 Smart Traffic Management System

**AI-driven, reinforcement-learning-based traffic signal control — from a single intersection to a coordinated multi-junction grid — built end-to-end with SUMO, PyTorch, FastAPI, and React.**

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://smart-traffic-system-sigma.vercel.app)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18-61DAFB)](https://react.dev/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#license)

---

## 🔗 Live Demo

**Dashboard:** [smart-traffic-system-sigma.vercel.app](https://smart-traffic-system-sigma.vercel.app)
**Backend API docs:** `https://<your-render-url>.onrender.com/docs`

> ⚠️ The backend runs on a free-tier cloud instance and may take 30–60 seconds to wake up on first load, and may occasionally restart due to memory limits. For the full experience (including the 2×2 multi-intersection grid), running locally is recommended — see [Setup](#-local-setup).

---

## 📸 Preview

| Single Intersection Dashboard | Multi-Intersection Grid |
|---|---|
| Live AI-controlled signal, queues, AI recommendation panel, manual override | 4 coordinated junctions with live fixed-vs-adaptive comparison |

*(Add your own screenshots here — drag them into the repo under `docs/screenshots/` and reference them, e.g. `![Dashboard](docs/screenshots/dashboard.png)`)*

---

## 📖 Overview

Traffic signals in most cities — including Indian intersections — run on **fixed timers**: a fixed number of seconds per direction, regardless of how much traffic is actually there. This wastes green time on empty roads while cars queue for minutes on busy ones.

This project replaces that fixed-timer logic with an **AI agent trained using Deep Q-Learning (DQN)** that watches live traffic (queue lengths, waiting times) and decides, every 10 seconds, whether to **hold** the current green light or **switch** to the next direction — learning, through thousands of simulated hours of traffic, exactly when each choice pays off.

The system is built specifically around **India-style signal logic**: one direction gets green at a time, rotating clockwise (North → East → South → West) — not the paired North-South / East-West logic common elsewhere — because that's the safer, more realistic pattern for dense, mixed Indian traffic.

It was built in two stages:
1. A **single intersection**, trained with a custom Gymnasium RL environment and a DQN agent (Stable-Baselines3 / PyTorch), achieving an **86–91% reduction in average vehicle wait time** versus a fixed 30-second timer.
2. A **2×2 grid of coordinated intersections**, controlled by a **pressure-based adaptive algorithm** (the same class of algorithm used in real-world traffic engineering), achieving a **72.3% reduction in system-wide wait time** versus the same fixed-timer baseline — while both use the identical India-style rotation, isolating the benefit to *timing intelligence alone*.

The full stack — simulation, AI training, backend, and live dashboard — is built from scratch and is fully deployed.

---

## ✨ Key Features

- 🧠 **Custom Deep Q-Network (DQN) agent** trained from scratch on a realistic SUMO traffic simulation
- 🚦 **India-style one-direction-at-a-time clockwise signal logic** (N → E → S → W), not the common NS/EW-paired approach
- 📊 **Live dashboard** — real-time signal state, per-direction queue/wait cards, animated intersection view, live wait-time chart
- 🤖 **AI recommendation panel** — shows the model's live Q-values and confidence, with an explanation of *why* it's recommending an action
- 🕹️ **Manual override system** — operators can force any direction green for a chosen duration, with the AI automatically resuming control afterward
- 🌐 **Multi-intersection 2×2 grid** — a second, independently coordinated simulation with a live fixed-vs-adaptive comparison and a "proof log" of every timing decision and why it was made
- 🗄️ **Full decision logging** to a SQLite database — every AI decision, override, and traffic snapshot is persisted
- ⚡ **Real-time WebSocket streaming** from backend to dashboard — no polling for live data
- ☁️ **Fully deployed** — Dockerized FastAPI backend on Render, React dashboard on Vercel

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SUMO Traffic Simulator                      │
│        (single intersection  +  2×2 multi-intersection grid)        │
└───────────────────────────────┬───────────────────────────────────┘
                                 │ TraCI (Python control interface)
┌───────────────────────────────▼───────────────────────────────────┐
│                          RL Engine (rl_engine/)                    │
│   Gymnasium environment · DQN agent (Stable-Baselines3/PyTorch)    │
│   Reward function · Fairness constraints · Signal program builder  │
└───────────────────────────────┬───────────────────────────────────┘
                                 │
┌───────────────────────────────▼───────────────────────────────────┐
│                      FastAPI Backend (backend/)                    │
│   Background simulation threads · REST API · WebSocket streaming   │
│   SQLite decision logging · Manual override handling               │
└───────────────────────────────┬───────────────────────────────────┘
                                 │ HTTP + WebSocket
┌───────────────────────────────▼───────────────────────────────────┐
│                    React Dashboard (dashboard/)                    │
│   Live intersection view · Signal cards · AI recommendation panel  │
│   Manual override controls · Multi-intersection grid view          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🧠 How the AI Works

**State (what the AI sees, every 10 seconds):**
A 10-feature vector — queue length and waiting time for each of the 4 directions, plus the current signal phase and how long it's been active — all normalized to `[0, 1]`.

**Action (what the AI can do):**
A binary choice: `KEEP` (hold the current green) or `SWITCH` (advance to the next direction in the fixed clockwise rotation).

**Reward (how the AI is scored):**
```
reward = -(total waiting time across all 4 directions) × weight
         − fairness penalty (if any direction is starved beyond a threshold)
         + efficiency bonus (for directions with zero queue)
```

**Safety constraints (rules the AI cannot break):**
A minimum green time (prevents unsafe rapid switching) and a maximum green time (prevents any one direction from hogging the cycle) are enforced independently of the AI's decision — the AI proposes, the constraint layer disposes.

**Training:** ~50,000 simulated timesteps (~150 episodes, each representing 1 hour of traffic) using DQN with an experience replay buffer and epsilon-greedy exploration, decaying from fully random to a 5%-exploration policy.

---

## 📊 Results

| Configuration | Metric | Fixed Timer | AI-Controlled | Improvement |
|---|---|---:|---:|---:|
| Single intersection | Avg. wait time | 543.2s | 48.6s | **91.1%** |
| Single intersection (re-trained run) | Avg. wait time | 2059.8s | 283.0s | **86.3%** |
| 2×2 grid (4 junctions) | System-wide total wait | 1809.9s | 500.8s | **72.3%** |

*Both fixed and AI-controlled runs use the identical India-style clockwise rotation — the only variable is how long each green phase lasts, isolating the improvement to the AI's adaptive timing decisions.*

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Traffic simulation | [SUMO](https://sumo.dlr.de/) (Simulation of Urban Mobility) + TraCI |
| Reinforcement learning | [Stable-Baselines3](https://stable-baselines3.readthedocs.io/) (DQN) · [Gymnasium](https://gymnasium.farama.org/) · PyTorch |
| Backend | [FastAPI](https://fastapi.tiangolo.com/) · SQLAlchemy · SQLite · WebSockets · Uvicorn |
| Frontend | [React](https://react.dev/) · [Vite](https://vitejs.dev/) · TailwindCSS · Recharts |
| Deployment | Docker · [Render](https://render.com/) (backend) · [Vercel](https://vercel.com/) (frontend) |

---

## 📁 Project Structure

```
smart-traffic-system/
├── simulation/                    # SUMO network + traffic demand definitions
│   └── nets/
│       ├── single_intersection/   # 4-way single junction
│       └── grid_2x2/              # 2×2 multi-intersection grid
├── rl_engine/                     # All AI/RL code
│   ├── environment/                # Gym environment, state/action/reward, signal logic
│   ├── agents/                     # DQN agent construction & configuration
│   ├── constraints/                 # Fairness / min-max green time rules
│   ├── training/                   # Training and evaluation scripts
│   ├── utils/                      # Logging, plotting
│   └── models/                     # Saved trained model checkpoints
├── backend/                       # FastAPI server
│   ├── main.py                     # App entry point, lifespan, routes registration
│   ├── services/                    # Simulation loop, RL inference, overrides
│   ├── database/                    # SQLAlchemy models, CRUD operations
│   ├── schemas/                     # Pydantic request/response models
│   └── api/                         # REST routes + WebSocket endpoints
├── dashboard/                     # React frontend
│   └── src/
│       ├── components/              # Signal cards, intersection view, charts, panels
│       ├── hooks/                   # Data fetching, WebSocket connections
│       └── services/                 # API client
├── data/                          # Logs, SQLite DB, evaluation results
└── Dockerfile                     # Backend container definition (includes SUMO)
```

---

## 🚀 Local Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- [SUMO](https://sumo.dlr.de/docs/Downloads.php) installed, with `SUMO_HOME` set

### 1. Clone and set up the Python environment
```bash
git clone https://github.com/<your-username>/smart-traffic-system.git
cd smart-traffic-system
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Generate the SUMO networks (if not already built)
```bash
cd simulation/nets/single_intersection
netconvert --node-files=nodes.nod.xml --edge-files=edges.edg.xml --output-file=network.net.xml --no-turnarounds true

cd ../grid_2x2
netconvert --node-files=nodes.nod.xml --edge-files=edges.edg.xml --output-file=network.net.xml --no-turnarounds true
```

### 3. Train the AI (or use the included pre-trained model)
```bash
cd ../../..   # back to project root
python rl_engine/training/train.py
```

### 4. Run the backend
```bash
cd backend
python main.py
```
API available at `http://localhost:8000`, interactive docs at `http://localhost:8000/docs`.

### 5. Run the dashboard
```bash
cd dashboard
npm install
npm run dev
```
Dashboard available at `http://localhost:5173`.

---

## 🧪 Evaluating the Model

Compare the trained AI against a fixed-timer baseline:
```bash
python rl_engine/training/evaluate.py            # single intersection
python rl_engine/training/evaluate_multi_transfer.py  # 2×2 grid
```

---

## 🗺️ Roadmap

- [ ] Reward shaping to reduce excessive phase-switching (currently the raw AI preference favors frequent rotation; the deployed system already constrains this with minimum green-time rules)
- [ ] True multi-agent reinforcement learning (joint training with inter-agent communication) for the grid, replacing the current pressure-based coordination
- [ ] Priority/rush-hour scheduling rules
- [ ] Support for larger grids (3×3, arbitrary topologies)
- [ ] Integration with live camera/IoT sensor feeds in place of simulated data

---

## 🙋 About This Project

Built as a self-directed learning project to go deep on reinforcement learning, simulation, and full-stack systems engineering — from a single Python script reading traffic data, all the way to a deployed, cloud-hosted, real-time AI dashboard.

**Author:** Hirak Jain
**Contact:** [LinkedIn](#) · [GitHub](#)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
