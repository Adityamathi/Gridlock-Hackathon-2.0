# ASTraM Event Congestion Command

Real-Time Traffic Incident Response System for Bengaluru Traffic Police  
**Theme:** Event-Driven Congestion (Planned & Unplanned)


---

## Overview

A decision-support dashboard that predicts severity, road closures, event duration, and resource deployment (officers, barricades, patrols) for traffic congestion events in Bengaluru. Trained on 8,200+ historical ASTraM events across 22 corridors using 6 scikit-learn models.

## Features

- **Interactive Map** — 22 Bangalore corridors, severity zones, diversion routes
- **ML Prediction Pipeline** — closure, duration, severity, resource optimization
- **Real-Time Monitoring** — SSE-based live events (simulation or TomTom API)
- **Feedback & Retraining** — edit ground truth, retrain models with one click
- **Corridor Routing** — graph-based alternate route computation

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
| **Analyze an event** | Analysis tab → pick corridor → pick event cause → click Analyze |
| **Feedback log** | Feedback Log tab → browse → edit ground truth → Save → Retrain Models |
| **Live Monitor** | Live Monitor tab → set Simulation → Start |
| **TomTom live traffic** | Live Monitor → TomTom Traffic API → enter key → Save → Start |

## Retrain All Models

```bash
python src/features.py
python src/train_all.py
python src/train_resource_model.py
```

## Tech Stack

- **Backend:** Flask, SSE
- **ML:** scikit-learn, pandas, numpy, joblib
- **Frontend:** Vanilla JS, Leaflet.js
- **Data:** 8,200+ historical ASTraM events

## License

MIT
