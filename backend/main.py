import os
import socket
import subprocess
import psutil
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],             # Explicitly allows Vercel domains to connect
    allow_credentials=False,         # Must be False if allow_origins is set to "*"
    allow_methods=["*"],             # Allows POST, GET, OPTIONS, PUT, DELETE
    allow_headers=["*"],             # Allows custom headers like ngrok-skip-browser-warning
    expose_headers=["*"],
)

SECRET_SLUG = "4f7d8a2c1b9e3f6a5d8c7b2a1e0f9b8a"

# 🧠 STATE MEMORY: Tracks user intent to prevent the UI from flickering/bouncing
LAST_TRIGGER_ACTION = "offline" 

def check_minecraft_status() -> str:
    global LAST_TRIGGER_ACTION
    java_running = False
    playit_running = False
    cmd_running = False
    
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            name = proc.info['name']
            cmdline = proc.info['cmdline']
            
            if not name:
                continue
            name_lower = name.lower()
            
            # Stringify the full command line argument array for quick checking
            cmdline_str = " ".join(cmdline).lower() if cmdline else ""
            
            # 1. Detect Java Server Instance
            if 'java' in name_lower:
                if 'server.jar' in cmdline_str or 'nogui' in cmdline_str:
                    java_running = True
                    
            # 2. Detect Playit Tunnel
            elif 'playit' in name_lower:
                playit_running = True
                
            # 3. Detect Active Launch Script
            elif 'cmd' in name_lower or 'powershell' in name_lower:
                if 'start_server' in cmdline_str:
                    cmd_running = True
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Debug log to terminal so you can see exactly what the backend discovers every 3s
    print(f"📊 [STATUS SCAN] Java: {java_running} | Playit: {playit_running} | Cmd: {cmd_running}")

    if java_running and playit_running:
        LAST_TRIGGER_ACTION = "online"
        return "online"
    elif cmd_running or java_running or playit_running:
        # 🛡️ If any component is alive but we explicitly toggled turn off, it's "stopping"
        if LAST_TRIGGER_ACTION == "stopping":
            return "stopping"
            
        LAST_TRIGGER_ACTION = "starting"
        return "starting"
    else:
        # 🛡️ Catch the brief microsecond gap when starting up
        if LAST_TRIGGER_ACTION == "starting":
            return "starting"
            
        LAST_TRIGGER_ACTION = "offline"
        return "offline"

@app.options("/{path:path}")
async def preflight_handler():
    return {"message": "ok"}

def get_server_process():
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if 'java' in proc.info['name'] and 'server.jar' in str(proc.info['cmdline']):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None

def is_port_open(port=25565):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        try:
            s.connect(('127.0.0.1', port))
            return True
        except (socket.timeout, ConnectionRefusedError):
            return False

@app.post(f"/validate-key/{SECRET_SLUG}")
def validate_key(payload: dict):
    if payload.get("key") == SECRET_SLUG:
        return {"valid": True}
    raise HTTPException(status_code=401, detail="Invalid access key")

@app.get("/status/{token}")
def get_status(token: str):
    if token != SECRET_SLUG:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    current_state = check_minecraft_status()
    
    # Map messages beautifully based on true state
    messages = {
        "online": "Server is up and running!",
        "starting": "Systems are booting up... Please wait.",
        "stopping": "Winding down server threads... Please wait.",
        "offline": "Server is currently offline."
    }
    
    return {"status": current_state, "message": messages.get(current_state, "Checking link metrics...")}

# The Switch Core: Handles both ON and OFF requests
@app.post(f"/trigger/{SECRET_SLUG}")
def trigger_switch(payload: dict):
    action = payload.get("action")  # "start" or "stop"
    global LAST_TRIGGER_ACTION
    
    try:
        # 🔍 Scan for both Java AND Playit before making decisions
        is_running = check_minecraft_status()
        
        if action == "start":
            if is_running != "offline":
                return {"status": "info", "message": f"Server is already {is_running}."}
            
            # Try project root first, then backend folder fallback
            root_dir = os.getcwd() # C:\gate\minecraft-server-switch
            script_path = os.path.join(root_dir, "start_server.bat")
            
            if not os.path.exists(script_path):
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                script_path = os.path.join(backend_dir, "start_server.bat")

            print(f"🚀 [DEBUG] Attempting to launch script at: {script_path}")
            
            if not os.path.exists(script_path):
                print(f"❌ [ERROR] start_server.bat was not found anywhere!")
                return {"status": "error", "message": "Launch script missing on host configuration."}

            # Run it detached so it survives even if Uvicorn recycles
            subprocess.Popen([script_path], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            
            LAST_TRIGGER_ACTION = "starting"
            return {"status": "starting", "message": "Booting engines..."}
            
        elif action == "stop":
            LAST_TRIGGER_ACTION = "stopping"
            terminated_any = False
            
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    name = proc.info['name']
                    cmdline = proc.info['cmdline']
                    
                    if not name:
                        continue
                        
                    name_lower = name.lower()
                    
                    # 1. Target the Minecraft Server (Java)
                    if 'java' in name_lower:
                        if cmdline and any('server.jar' in arg.lower() or 'nogui' in arg.lower() for arg in cmdline):
                            subprocess.run(["taskkill", "/pid", str(proc.pid), "/f", "/t"], capture_output=True)
                            terminated_any = True
                            
                    # 2. Target the Playit Connection Tunnel
                    elif 'playit' in name_lower:
                        subprocess.run(["taskkill", "/pid", str(proc.pid), "/f"], capture_output=True)
                        terminated_any = True

                    # 3. Target the parent command prompt wrapper holding the window open
                    elif 'cmd' in name_lower:
                        if cmdline and any('start_server.bat' in arg.lower() for arg in cmdline):
                            subprocess.run(["taskkill", "/pid", str(proc.pid), "/f"], capture_output=True)
                            terminated_any = True
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {"status": "stopping", "message": "Shutdown sequence initiated."}
                
        raise HTTPException(status_code=400, detail="Invalid action")

    except Exception as e:
        print(f"Trigger execution error: {e}")
        return {"status": "error", "message": f"Internal host handler error: {e}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
