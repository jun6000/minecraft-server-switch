# ⏻ Minecraft Server Remote Switcher

A lightweight, secure, self-hosted automation pipeline that allows remote users to spin up or gracefully shut down a local Minecraft server and its network tunnel via a slick, modern web dashboard hosted on Vercel.

---

## 🏗️ Architecture Overview

The system uses a frictionless, zero-database design to manage power states and authentication:

* **Frontend (Vercel):** A Tailwind CSS static dashboard that securely caches access tokens in the browser's native `localStorage`. It features a live-polling iOS-style toggle track that switches states (Offline -> Starting -> Online).
* **Secure Network Bridge (Ngrok):** An encrypted HTTPS tunnel exposing only the specific backend gateway over a free permanent static domain.
* **Backend (FastAPI & Windows OS):** A lightweight API that handles route-level authentication using a private "Webhook Slug" pattern. It dynamically inspects the OS process tree (`psutil`) and tests active TCP socket binds (`port 25565`) to report absolute server initialization states.

---

## 📂 Project Structure

minecraft-server-switch/
├── backend/
│   ├── main.py              # FastAPI core application & process tracking
│   ├── start_server.bat     # Process guard & minimized launcher for Java & Playit
│   └── stop_server.bat      # Graceful task killer for clean world-map saving
├── index.html               # Tailwind CSS dashboard (deployed to Vercel)
└── README.md                # System documentation

---

## ⚡ Quick Start & Deployment

### 1. Local Host Machine Configuration
Ensure you have Python 3.10+ installed along with the required system hooks:
Command: pip install fastapi uvicorn psutil

Authorize your Ngrok agent locally with your account authtoken to unlock static domains:
Command: ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN

### 2. Booting the Pipeline
To fire up the environment on your host workstation, run the API and tunnel concurrently in separate terminals:

Terminal A (FastAPI Gateway):
Command: uvicorn backend.main:app --reload

Terminal B (Secure Static Tunnel):
Command: ngrok http 8000 --url=your-chosen-name.ngrok-free.app

### 3. Vercel Deployment
1. Ensure your static Ngrok URL is defined inside the `BASE_URL` constant within `index.html`.
2. Commit and push the project files to your linked GitHub repository.
3. Import the repository into the Vercel Dashboard and hit Deploy.

---

## 🔒 Security Implementation Details

Rather than utilizing traditional heavy request-body parsing or exposed auth headers, this setup implements a Route Matching / Webhook Slug pattern. 

The user's 32-character access hash is embedded directly into the URI path structure (/status/{SECRET_SLUG}). If unauthorized web traffic or automated scrapers attempt to hit your public Ngrok tunnel, the application routing table drops the request at the framework gateway with an immediate 404 Not Found, ensuring unauthorized queries never reach the inner execution logic or touch system subprocess routines.
