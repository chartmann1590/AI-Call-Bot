#!/usr/bin/env python3
"""
Main entry point for AI Call Bot application.
This file serves as a bridge to the src directory.
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main application
from main import main

if __name__ == "__main__":
    main() 