import subprocess
import sys
import os

def run_cmd(args):
    print(f"Running: {' '.join(args)}")
    try:
        subprocess.check_call(args)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        sys.exit(1)

def main():
    # 1. Install/Update dependencies
    print("Step 1: Installing/Updating dependencies from requirements.txt...")
    # Use the current python executable to install requirements
    run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    # 2. Run uvicorn
    print("\nStep 2: Starting the application server (SIGFolha)...")
    print("The backend serves both the API and the frontend user interface.")
    print("Once started, open your browser at: http://127.0.0.1:8000\n")
    try:
        # Run uvicorn using the same python executable
        subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--reload"])
    except KeyboardInterrupt:
        print("\nApplication stopped by user.")

if __name__ == "__main__":
    main()
