#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys
from pathlib import Path


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "detectiq.webapp.backend.settings")

    # Add the project root to the Python path
    project_root = Path(__file__).resolve().parent
    sys.path.append(str(project_root))

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django. Are you sure it's installed?") from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
