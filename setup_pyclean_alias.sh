#!/bin/bash
"""
Setup PyClean alias for easy cache clearing

This script sets up the pyclean alias in your shell profile.
Run this once to set up the alias, then you can use 'pyclean' as a hotkey.

Usage:
    bash setup_pyclean_alias.sh
"""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create the alias command
ALIAS_COMMAND="alias pyclean='cd $SCRIPT_DIR && python3 pyclean.py'"

# Check which shell profile to use
if [ -f ~/.zshrc ]; then
    PROFILE_FILE=~/.zshrc
    SHELL_NAME="zsh"
elif [ -f ~/.bashrc ]; then
    PROFILE_FILE=~/.bashrc
    SHELL_NAME="bash"
else
    echo "❌ Could not find .zshrc or .bashrc file"
    exit 1
fi

echo "🔧 Setting up pyclean alias for $SHELL_NAME..."

# Check if alias already exists
if grep -q "alias pyclean=" "$PROFILE_FILE"; then
    echo "ℹ️  pyclean alias already exists in $PROFILE_FILE"
    echo "   Current alias:"
    grep "alias pyclean=" "$PROFILE_FILE"
else
    # Add the alias to the profile
    echo "" >> "$PROFILE_FILE"
    echo "# PyClean alias for cache clearing" >> "$PROFILE_FILE"
    echo "$ALIAS_COMMAND" >> "$PROFILE_FILE"
    echo "✅ Added pyclean alias to $PROFILE_FILE"
fi

echo ""
echo "🎯 Setup complete! To use the alias:"
echo "   1. Restart your terminal or run: source $PROFILE_FILE"
echo "   2. Then you can use: pyclean"
echo ""
echo "📋 Available commands:"
echo "   pyclean                    # Quick cache clear (no confirmation)"
echo "   python3 manage_cache.py status    # Check cache status"
echo "   python3 manage_cache.py clear     # Clear with confirmation"
