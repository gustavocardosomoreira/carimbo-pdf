"""Versão compartilhada pela API, interface web e aplicativo desktop."""

import os
import subprocess
from pathlib import Path
from typing import Optional


APP_VERSION = "1.1.1"


def _get_commit() -> Optional[str]:
    """Identifica o código publicado, mesmo sem o Git instalado na nuvem."""
    for variable in ("APP_COMMIT_SHA", "RAILWAY_GIT_COMMIT_SHA"):
        commit = os.environ.get(variable, "").strip()
        if commit:
            return commit

    repository_dir = Path(__file__).resolve().parent.parent
    if not (repository_dir / ".git").exists():
        return None

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return None

    return result.stdout.strip() or None


APP_COMMIT = _get_commit()
