import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        raise ValueError(
            f"Missing environment variable {name}. "
            "Copy .env.example to .env and fill in your keys — see SETUP.md."
        )
    return val


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


MARKETCHECK_API_KEY: str = _optional("MARKETCHECK_API_KEY")
AUTODEV_API_KEY: str = _optional("AUTODEV_API_KEY")
DRIVLY_API_KEY: str = _optional("DRIVLY_API_KEY")
CARAPIS_API_KEY: str = _optional("CARAPIS_API_KEY")

MONGODB_URI: str = _optional("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME: str = _optional("MONGODB_DB_NAME", "ev_comparison")
