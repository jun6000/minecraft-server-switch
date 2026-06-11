# ⏻ Minecraft Server Remote Switcher

A lightweight, secure, self-hosted automation pipeline that allows remote users to spin up or gracefully shut down a local Minecraft server and its network tunnel via a slick, modern web dashboard hosted on Vercel.

---

## 🏗️ Architecture Overview

The system uses a frictionless, zero-database design to manage power states and authentication:

* **Frontend (Vercel):** A Tailwind CSS static dashboard that securely caches access tokens in the browser's native `localStorage`. It features a live-polling iOS-style toggle track that switches states (**Offline** ➡️ **Starting** ➡️ **Online**).
* **Secure Network Bridge (Ngrok):** An encrypted HTTPS tunnel exposing only the specific backend gateway over a free permanent static domain.
* **Backend (FastAPI & Windows OS):** A lightweight API that handles route-level authentication using a private "Webhook Slug" pattern. It dynamically inspects the OS process tree (`psutil`) and tests active TCP socket binds (`port 25565`) to report absolute server initialization states.

---

## 📂 Project Structure

```text
minecraft-server-switch/
├── backend/
│   ├── main.py              # FastAPI core application & process tracking
│   ├── start_server.bat     # Process guard & minimized launcher for Java & Playit
│   └── stop_server.bat      # Graceful task killer for clean world-map saving
├── index.html               # Tailwind CSS dashboard (deployed to Vercel)
└── README.md                # System documentation
