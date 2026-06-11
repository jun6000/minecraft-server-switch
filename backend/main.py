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

def check_minecraft_process() -> bool:
    """
    Scans running system processes. 
    Returns True ONLY if BOTH the Minecraft server (Java) AND the playit tunnel client are running.
    """
    java_running = False
    playit_running = False
    
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            name = proc.info['name']
            cmdline = proc.info['cmdline']
            
            if not name:
                continue
                
            name_lower = name.lower()
            
            # 1. Check for the Minecraft Server (Java instance with server flags)
            if 'java' in name_lower:
                if cmdline and any('server.jar' in arg.lower() or 'nogui' in arg.lower() for arg in cmdline):
                    java_running = True
                    
            # 2. Check for the Playit Tunnel Client
            # Usually named 'playit.exe' on Windows, or contains 'playit' in the command line
            elif 'playit' in name_lower:
                playit_running = True
                
            # Quick escape: if we found both, no need to keep searching the process tree
            if java_running and playit_running:
                return True
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
            
    return java_running and playit_running

@app.options("/{path:path}")
async def preflight_handler():
    return {"message": "ok"}

SECRET_SLUG = "4f7d8a2c1b9e3f6a5d8c7b2a1e0f9b8a"

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
    # Verify token
    if token != SECRET_SLUG:
        # Instead of raising HTTPException(401), return a clean dictionary response!
        return {"status": "offline", "message": "Unauthorized session access."}
        
    try:
        # Your original code that checks if the server is running...
        is_running = check_minecraft_process()
        
        if is_running:
            return {"status": "online", "message": "Server is actively running."}
        else:
            return {"status": "offline", "message": "Server is currently stopped."}
            
    except Exception as e:
        print(f"Internal wrapper error: {e}")
        # Return a fallback JSON state instead of letting Python crash!
        return {"status": "offline", "message": "Host connection offline."}

# The Switch Core: Handles both ON and OFF requests
@app.post(f"/trigger/{SECRET_SLUG}")
def trigger_switch(payload: dict):
    action = payload.get("action")  # "start" or "stop"
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        # 🔍 Scan for both Java AND Playit before making decisions
        is_running = check_minecraft_process()
        
        if action == "start":
            if is_running:
                # 🛑 Early guardrail exit - completely blocks running start_server.bat
                return {"status": "info", "message": "Server and tunnel are already running."}
            
            script_path = os.path.join(backend_dir, "start_server.bat")
            subprocess.Popen([script_path], shell=True)
            return {"status": "starting", "message": "Booting engines..."}
            
        elif action == "stop":
            terminated_any = False
            
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    name = proc.info['name']
                    cmdline = proc.info['cmdline']
                    
                    if not name:
                        continue
                        
                    name_lower = name.lower()
                    
                    # 1. Target the Minecraft Server via its PID
                    if 'java' in name_lower:
                        if cmdline and any('server.jar' in arg.lower() or 'nogui' in arg.lower() for arg in cmdline):
                            # Adding /f forces the stubborn background Java instance to close instantly
                            subprocess.run(["taskkill", "/pid", str(proc.pid), "/f", "/t"], capture_output=True)
                            terminated_any = True
                            
                    # 2. Target the Playit Connection Tunnel
                    elif 'playit' in name_lower:
                        subprocess.run(["taskkill", "/pid", str(proc.pid), "/f"], capture_output=True)
                        terminated_any = True
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if terminated_any:
                return {"status": "offline", "message": "Shutdown sequence initiated."}
            else:
                return {"status": "info", "message": "No active processes discovered to close."}
                
        raise HTTPException(status_code=400, detail="Invalid action")

    except Exception as e:
        print(f"Trigger execution error: {e}")
        return {"status": "error", "message": f"Internal host handler error: {e}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
