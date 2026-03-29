import os
import sys
import psutil
import socket

def run_audit():
    print("\n" + "="*60)
    print("📡 POWERPLANT AI: SYSTEM CLOUD AUDIT")
    print("="*60)
    
    # 1. OS & Python
    print(f"[SYSTEM] OS: {sys.platform}")
    print(f"[SYSTEM] Python: {sys.version}")
    
    # 2. RAM Audit
    mem = psutil.virtual_memory()
    total_mb = mem.total / (1024 * 1024)
    avail_mb = mem.available / (1024 * 1024)
    print(f"[MEMORY] Total RAM: {total_mb:.1f} MB")
    print(f"[MEMORY] Available RAM: {avail_mb:.1f} MB")
    
    if total_mb < 600:
        print("[WARNING] Low Memory Detected. Pitting TensorFlow against strict RAM limits.")
    
    # 3. Network Check
    try:
        host = socket.gethostbyname("pypi.org")
        print(f"[NETWORK] PyPI Connectivity: Success (IP: {host})")
    except Exception as e:
        print(f"[NETWORK] PyPI Connectivity: FAILED ({e})")
        
    print("="*60 + "\n")

if __name__ == "__main__":
    run_audit()
