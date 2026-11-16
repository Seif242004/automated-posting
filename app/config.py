import os

from dotenv import load_dotenv

load_dotenv()


def env(name: str, default: str = "") -> str:
    """Read a credential from the environment (empty string if unset)."""
    return os.environ.get(name, default).strip()


REQUEST_TIMEOUT = float(env("REQUEST_TIMEOUT", "15"))
MAX_MESSAGE_LENGTH = 200
