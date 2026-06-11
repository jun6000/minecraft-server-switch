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
        # e.g., is_running = check_minecraft_process()
        
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
    action = payload.get("action") # "start" or "stop"
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    if action == "start":
        if get_server_process():
            return {"status": "info", "message": "Already running."}
        
        script_path = os.path.join(backend_dir, "start_server.bat")
        subprocess.Popen([script_path], shell=True)
        return {"message": "Booting engines..."}
        
    elif action == "stop":
        if not get_server_process():
            return {"status": "info", "message": "Already stopped."}
            
        script_path = os.path.join(backend_dir, "stop_server.bat")
        subprocess.Popen([script_path], shell=True)
        return {"message": "Shutting down systems..."}
        
    raise HTTPException(status_code=400, detail="Invalid action")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
