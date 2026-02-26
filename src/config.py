"""Config loader — reads YAML and resolves ${ENV_VAR} placeholders."""

import os
import re
import yaml


def load_config(path: str) -> dict:
    """Load YAML config and substitute ${VAR} patterns from environment."""
    with open(path, "r") as f:
        raw = f.read()

    # Replace ${VAR} with env value or leave as placeholder
    def sub(match: re.Match) -> str:
        var = match.group(1)
        return os.environ.get(var, f"<{var}_NOT_SET>")

    resolved = re.sub(r"\$\{(\w+)\}", sub, raw)
    return yaml.safe_load(resolved)
