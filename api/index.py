"""
Vercel entrypoint for FastAPI backend
This file imports the FastAPI app from api_server.py
"""
import sys
import os

# Add parent directory to path so we can import api_server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app
from api_server import app

# Export for Vercel
__all__ = ['app']

