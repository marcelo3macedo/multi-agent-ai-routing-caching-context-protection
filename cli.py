#!/usr/bin/env python3
"""
Ponto de entrada da CLI Terminal (Clean Architecture Presentation Layer).
"""
import sys
from src.presentation.cli.main import app

if __name__ == "__main__":
    if len(sys.argv) == 1:
        app(["repl"])
    else:
        app()
