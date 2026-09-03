#!/bin/bash

# Exit on error
set -e

echo "🚀 Setting up Deep Research Agent on Fedora..."

# System dependencies
echo "📦 Installing system dependencies..."
sudo dnf update -y
sudo dnf install -y python3 python3-pip python3-virtualenv
sudo dnf install -y libffi-devel openssl-devel

# Create virtual environment
echo "🐍 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp configs/.env.example .env
    echo "⚠️  Remember to edit .env with your API keys!"
fi

echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To start the server:"
echo "  python -m sih_hackathon.main"