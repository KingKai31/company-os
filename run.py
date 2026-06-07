import sys
import threading
import webbrowser

from dotenv import load_dotenv

load_dotenv()

from app import app

URL = "http://localhost:5000"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def open_browser():
    webbrowser.open(URL)


def warmup_check():
    try:
        from utils.shared_brain import read_all_states
        states = read_all_states()
        print(f"[STARTUP] Cosmos DB connected ({len(states)} agent states)")
    except Exception as e:
        print(f"[STARTUP] Cosmos DB warning: {e} (pipeline will retry with timeout)")


if __name__ == "__main__":
    print(f"◈ COMPANY OS RUNNING AT {URL}")
    print(f"◈ Architecture: {URL}/static/architecture.html")
    print(f"◈ Press Ctrl+C to stop\n")
    warmup_check()
    threading.Timer(1.0, open_browser).start()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
