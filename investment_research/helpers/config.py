"""Configuration and environment management."""

import os
from dotenv import load_dotenv


def load_and_validate_env():
    """
    Loads environment variables (optionally from .env) and validates required keys.
    In Codespaces, set these as Codespaces Secrets (recommended).

    Raises:
        ValueError: If required environment variables are missing
    """
    load_dotenv()  # if no .env exists, this does nothing

    required = ["OPENAI_API_KEY", "FMP_API_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise ValueError(
            "Missing required environment variables: "
            + ", ".join(missing)
            + "\n\nSet them in GitHub: Repo Settings -> Secrets and variables -> Codespaces.\n"
            "Or create a local .env file for development (DO NOT commit it)."
        )

    # Disable OpenTelemetry if you want quieter logs
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")
