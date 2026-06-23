# Grid Unlock Command

Real-Time Traffic Incident Response System for Bengaluru Traffic Police  
**Theme:** Event-Driven Congestion (Planned & Unplanned)

---

## Overview

A decision-support dashboard that predicts severity, road closures, event duration, and resource deployment (officers, barricades, patrols) for traffic congestion events in Bengaluru. Trained on 7,500+ historical ASTraM events across **147 corridors** (21 named + 125 address-extracted non-corridor roads) using 6 scikit-learn models.

## Features

- **Interactive Map** — 147 Bangalore corridors with severity zones, diversion routes, and junction markers
- **ML Prediction Pipeline** — closure (84.6%), duration (56.9%), severity (76.3%), and resource optimization
- **Real-Time Monitoring** — SSE-based live events (simulation or TomTom Traffic API) with server-side start/stop
- **Feedback & Retraining** — ground truth correction, threaded CSV logging, one-click retrain of all 6 models
- **Corridor Routing** — graph-based alternate route computation across 147-node network
- **Two-Level Corridor Selector** — category (Corridor/Non-corridor) then road selector
- **Result Dashboard** — dynamic "Why this result" reasoning, escalation notes, attendance-aware resource scaling
- **Caution Notice** — resource numbers shown as minimum requirements; actual needs may vary in real-time conditions

## Quick Start

### Step 1 — Get the code

**Option A: Clone via Git**
```bash
git clone https://github.com/Adityamathi/Gridlock-Hackathon-2.0.git
cd Gridlock-Hackathon-2.0
```

**Option B: Download ZIP**
1. Go to https://github.com/Adityamathi/Gridlock-Hackathon-2.0
2. Click **Code** → **Download ZIP**
3. Extract the ZIP and open a terminal inside the extracted folder

### Step 2 — Install & Run

Open a terminal in the project folder and run:

```bash
pip install -r requirements.txt
python server.py
```

Open **http://localhost:5555** in your browser.

## How to Use

| Feature | Steps |
|---------|-------|
| **Analyze an event** | Analysis tab → select corridor category → pick road → pick event cause → click Run Analysis |
| **Load demo case** | Click **Load Demo** → review pre-filled fields → click Run Analysis |
| **Feedback log** | Feedback Log tab → browse/filter/sort → select an event → edit Ground Truth → Submit → Retrain Models |
| **Clear filters** | Click **Clear Sort** to reset all filters, sort, and pagination |
| **Live Monitor** | Live Monitor tab → set Simulation → Start → Stop to end |
| **TomTom live traffic** | Live Monitor → TomTom Traffic API → enter API key → Save → Start |
| **Retrain models** | Feedback Log tab → click **Retrain Models** (uses accumulated ground truth) |

## Resource Predictions

All resource numbers (officers, barricades, patrol vehicles) displayed in the dashboard are **minimum requirements** — actual needs may vary depending on real-time conditions, crowd behavior, and on-ground coordination.

## Retrain All Models

```bash
python src/features.py
python src/train_all.py
python src/train_resource_model.py
```

## Tech Stack

- **Backend:** Flask, SSE, joblib
- **ML:** scikit-learn, pandas, numpy, joblib
- **Frontend:** Vanilla JS, Leaflet.js
- **Data:** 7,500+ historical ASTraM events on 147 corridors

## License

MIT
