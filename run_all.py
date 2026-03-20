# run_all.py - Start both API and Streamlit
import subprocess
import time
import webbrowser
import sys
import os
import signal

def run_servers():
    """Start both FastAPI and Streamlit servers"""
    
    print("🚀 Starting Workflow Builder...")
    print("=" * 50)
    
    # Start FastAPI in background
    print("📡 Starting FastAPI server on http://localhost:8000...")
    api_process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for API to start
    time.sleep(3)
    
    # Check if API started successfully
    try:
        import requests
        requests.get("http://localhost:8000/health", timeout=2)
        print("-->> FastAPI server is running!")
    except:
        print("⚠️  FastAPI startup - waiting...")
    
    print("=" * 50)
    
    # Start Streamlit
    print("🎨 Starting Streamlit frontend on http://localhost:8501...")
    streamlit_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "streamlit_app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    time.sleep(2)
    print("-->> Streamlit frontend is running!")
    
    print("=" * 50)
    print("\n🌐 Opening browser...\n")
    
    # Open browser to Streamlit
    try:
        webbrowser.open("http://localhost:8501")
    except:
        print("Please open http://localhost:8501 in your browser")
    
    print("=" * 50)
    print("--> Available URLs:")
    print("  • Streamlit Frontend: http://localhost:8501")
    print("  • FastAPI Server: http://localhost:8000")
    print("  • API Docs: http://localhost:8000/docs")
    print("=" * 50)
    print("\nPress Ctrl+C to stop both servers...\n")
    
    # Keep running until interrupted
    try:
        api_process.wait()
        streamlit_process.wait()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down servers...")
        api_process.terminate()
        streamlit_process.terminate()
        
        # Wait for graceful shutdown
        try:
            api_process.wait(timeout=5)
            streamlit_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Force killing processes...")
            api_process.kill()
            streamlit_process.kill()
        
        print("-->> Servers stopped")

if __name__ == "__main__":
    try:
        run_servers()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
