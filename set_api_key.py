#!/usr/bin/env python3
"""
Simple script to update the API key in config.py
"""

import os

def update_api_key():
    """Update the API key in config.py"""
    print("🔑 NFL Player Prop Optimizer - API Key Setup")
    print("=" * 50)
    
    # Get API key from user
    api_key = input("Enter your API key from https://the-odds-api.com/: ").strip()
    
    if not api_key:
        print("❌ No API key provided. Exiting.")
        return
    
    # Read current config file
    config_path = "config.py"
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        return
    
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Replace the API key
    old_key = 'ODDS_API_KEY = "5fcc5a130a5bf4e22fa51c033d9a7c1a"'
    new_key = f'ODDS_API_KEY = "{api_key}"'
    
    if old_key in content:
        content = content.replace(old_key, new_key)
    else:
        # Try to find and replace any existing key
        import re
        pattern = r'ODDS_API_KEY = "[^"]*"'
        content = re.sub(pattern, new_key, content)
    
    # Write updated config
    with open(config_path, 'w') as f:
        f.write(content)
    
    print(f"✅ API key updated successfully!")
    print(f"🔑 New key: {api_key[:10]}...")
    print("\n🚀 You can now run the application with:")
    print("   streamlit run player_prop_optimizer.py")

if __name__ == "__main__":
    update_api_key()
