import os
import socket
import subprocess
import psutil
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.post("/validate-key")
def validate_key(payload: dict):
    if payload.get("key") == SECRET_SLUG:
        return {"valid": True}
    raise HTTPException(status_code=401, detail="Invalid access key")

@app.get(f"/status/{SECRET_SLUG}")
def get_status():
    proc = get_server_process()
    if not proc:
        return {"status": "offline", "message": "Server is stopped"}
    if is_port_open():
        return {"status": "online", "message": "Server is online!"}
    return {"status": "starting", "message": "Server is initializing..."}

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
