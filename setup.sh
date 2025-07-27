#!/bin/bash

# Setup script for Git Commit Reviewer

echo "Setting up Git Commit Reviewer..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setup complete!"
echo ""
echo "To use the tool:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Set your OpenAI API key: export OPENAI_API_KEY='your-key-here'"
echo "3. Run the tool: python git_commit_reviewer.py"
echo ""
echo "For help: python git_commit_reviewer.py --help"