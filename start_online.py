import os
import sys
import time
import subprocess
from pyngrok import ngrok

def start_online():
    # 1. Start Streamlit in the background
    print("Starting Streamlit app...")
    streamlit_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Give Streamlit a moment to start
    time.sleep(3)
    
    # 2. Start ngrok tunnel
    try:
        # Open a HTTP tunnel on the default port 8501
        # If you have an authtoken, you can set it here or via `ngrok config add-authtoken <token>`
        public_url = ngrok.connect(8501).public_url
        print("\n" + "="*50)
        print(f"YOUR APP IS ONLINE AT: {public_url}")
        print("="*50 + "\n")
        print("Share this link with your customers to let them test the app.")
        print("Keep this script running to keep the link active.")
        print("Press Ctrl+C to stop.")
        
        # Keep the script running
        streamlit_process.wait()

    except KeyboardInterrupt:
        print("\nStopping...")
        ngrok.kill()
        streamlit_process.terminate()
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        ngrok.kill()
        streamlit_process.terminate()
        sys.exit(1)

if __name__ == "__main__":
    start_online()
