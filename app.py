"""SmartAudit AI - run with:  python app.py   (or press the Run button in VS Code)

First run: installs the required packages automatically, then starts the
server and opens http://localhost:8000 in your browser.
"""
import importlib.util
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
PORT = int(os.getenv("PORT", "8000"))
MODULES = ["fastapi", "uvicorn", "multipart", "pandas", "numpy", "torch", "shap", "sklearn", "reportlab", "jwt"]


def install_missing():
    if all(importlib.util.find_spec(m) for m in MODULES):
        return
    print("Installing required packages (first run only, takes several minutes)...")
    pip = [sys.executable, "-m", "pip", "install"]
    if not importlib.util.find_spec("torch"):
        subprocess.check_call(pip + ["torch", "--index-url", "https://download.pytorch.org/whl/cpu"])
    subprocess.check_call(pip + ["-r", str(BACKEND / "requirements.txt")])


def main():
    install_missing()
    import uvicorn

    os.chdir(BACKEND)                      # the database file is created in backend/
    sys.path.insert(0, str(BACKEND))       # lets Python find the "app" package
    threading.Timer(3, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    print(f"SmartAudit AI running at http://localhost:{PORT}  (press Ctrl+C to stop)")
    uvicorn.run("app.main:app", host="127.0.0.1", port=PORT)


if __name__ == "__main__":
    main()
