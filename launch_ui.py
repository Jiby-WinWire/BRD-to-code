"""
Launcher script for the Web UI
Run with: python launch_ui.py
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Launch the Streamlit web application"""
    
    print("=" * 80)
    print("🚀 BRD-to-Code Pipeline - Web Dashboard")
    print("=" * 80)
    print()
    print("Starting web server...")
    print("The dashboard will open in your browser automatically.")
    print()
    print("Press Ctrl+C to stop the server.")
    print("=" * 80)
    print()
    
    # Path to the Streamlit app
    app_path = Path(__file__).parent / "src" / "ui" / "app.py"
    
    # Launch Streamlit
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port=8501",
        "--server.headless=false",
        "--browser.gatherUsageStats=false"
    ])

if __name__ == "__main__":
    main()
