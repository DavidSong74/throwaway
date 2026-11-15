"""Read a local dotenv file without shell execution, interpolation, or secret output."""
import os
from pathlib import Path
import re
import shlex


ALLOWED = {"DAYTONA_API_KEY", "DAYTONA_API_URL", "DAYTONA_V2_API_URL", "DAYTONA_API_VERSION",
           "NOSANA_API_KEY", "NOSANA_MODEL_ID", "NOSANA_API_BASE", "NOSANA_REQUEST_TIMEOUT"}


def load_local_env(path=Path(".env")):
    path = Path(path)
    if not path.is_file():
        return
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        text = re.sub(r"^export\s+", "", text)
        if "=" not in text:
            raise ValueError(f"Invalid .env assignment on line {number}")
        key, value = text.split("=", 1)
        key = key.strip()
        if key not in ALLOWED:
            continue
        try:
            parts = shlex.split(value, comments=True, posix=True)
        except ValueError:
            raise ValueError(f"Invalid .env quoting on line {number}") from None
        if len(parts) > 1:
            raise ValueError(f"Quote the .env value on line {number}")
        os.environ.setdefault(key, parts[0] if parts else "")
