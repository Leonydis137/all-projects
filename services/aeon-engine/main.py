#!/usr/bin/env python3
"""
AEON: The Conscious Context Engine
----------------------------------
Main entry point for the application.
"""

from aeon.core.app import AeonApp

def main():
    """Initialize and run the AEON application."""
    app = AeonApp()
    app.run()

if __name__ == "__main__":
    main()
