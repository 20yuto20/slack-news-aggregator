import os
import sys
from pathlib import Path

# Add the project directory to Python path
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

# Import the function from src/main.py
from src.main import new_collector

# Re-export the function
# This makes it available to Firebase Functions