#!/usr/bin/env python3
"""
Startup script for the NFL Player Prop Optimizer
"""

import subprocess
import sys
import os

def main():
    """Start the Streamlit application"""
    print("🏈 Starting NFL Player Prop Optimizer...")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('player_prop_optimizer.py'):
        print("❌ Error: player_prop_optimizer.py not found")
        print("Please run this script from the PropOptimizer directory")
        sys.exit(1)
    
    # Check if config.py exists
    if not os.path.exists('config.py'):
        print("❌ Error: config.py not found")
        print("Please ensure config.py exists with your API key")
        sys.exit(1)
    
    print("✅ Configuration files found")
    print("🚀 Starting Streamlit application...")
    print("📱 The app will open in your browser at http://localhost:8501")
    print("🛑 Press Ctrl+C to stop the application")
    print("=" * 50)
    
    try:
        # Start Streamlit
        subprocess.run([
            'streamlit', 'run', 'player_prop_optimizer.py',
            '--server.port', '8501',
            '--server.address', 'localhost'
        ])
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
