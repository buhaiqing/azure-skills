#!/usr/bin/env python3
"""
Azure Skills Environment Setup

1. Copies .env.example to .env if .env does not exist
2. Reads .env and generates azure-skill-generator/config.yaml with actual values
3. Renders {{env.*}} placeholders in template files using .env values

Usage:
    python azure-skill-generator/scripts/setup_env.py              # Full setup
    python azure-skill-generator/scripts/setup_env.py --check      # Only validate .env
    python azure-skill-generator/scripts/setup_env.py --render     # Only render config from .env
"""

import argparse
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
ENV_FILE = PROJECT_ROOT / ".env"
GENERATOR_ROOT = Path(__file__).resolve().parent.parent
GENERATOR_CONFIG = GENERATOR_ROOT / "config.yaml"
GENERATOR_EXAMPLE_CONFIG = GENERATOR_ROOT / "assets" / "example-config.yaml"

REQUIRED_AZURE_VARS = [
    "AZURE_SUBSCRIPTION_ID",
    "AZURE_TENANT_ID",
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
]

OPTIONAL_AZURE_VARS = [
    "AZURE_DEFAULT_LOCATION",
    "AZURE_REGION",
]


def parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse a .env file and return a dict of key-value pairs."""
    env_vars: dict[str, str] = {}
    if not env_path.exists():
        return env_vars

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if value and len(value) >= 2:
                if (value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"):
                    value = value[1:-1]
            env_vars[key] = value
    return env_vars


def copy_env_example() -> bool:
    """Copy .env.example to .env if .env does not exist."""
    if ENV_FILE.exists():
        print(f"  [OK]  .env already exists")
        return True

    if not ENV_EXAMPLE.exists():
        print(f"  [FAIL] .env.example not found at {ENV_EXAMPLE}")
        return False

    content = ENV_EXAMPLE.read_text(encoding="utf-8")
    ENV_FILE.write_text(content, encoding="utf-8")
    print(f"  [OK]  Created .env from .env.example")
    print(f"  [INFO] Please edit .env and fill in your Azure credentials")
    return True


def validate_env(env_vars: dict[str, str]) -> bool:
    """Validate that required Azure environment variables are set."""
    all_ok = True
    for var in REQUIRED_AZURE_VARS:
        value = env_vars.get(var, "")
        if not value or value.startswith("your_"):
            print(f"  [WARN] {var} is not set or still has placeholder value")
            all_ok = False
        else:
            print(f"  [OK]  {var} = {value[:8]}...")
    return all_ok


def generate_config(env_vars: dict[str, str]) -> None:
    """Generate azure-skill-generator/config.yaml from .env values."""
    sub_id = env_vars.get("AZURE_SUBSCRIPTION_ID", "your_subscription_id_here")
    tenant_id = env_vars.get("AZURE_TENANT_ID", "your_tenant_id_here")
    client_id = env_vars.get("AZURE_CLIENT_ID", "your_client_id_here")
    client_secret = env_vars.get("AZURE_CLIENT_SECRET", "your_client_secret_here")
    location = env_vars.get("AZURE_DEFAULT_LOCATION") or env_vars.get("AZURE_REGION") or "eastus"

    config_content = f"""# Azure Skill Generator Configuration
# Auto-generated from .env by azure-skill-generator/scripts/setup_env.py
# DO NOT commit this file to version control

# Azure Credentials
azure:
  subscription_id: "{sub_id}"
  tenant_id: "{tenant_id}"
  client_id: "{client_id}"
  client_secret: "{client_secret}"
  default_location: "{location}"

# Generation Settings
generation:
  cli_first: true
  sdk_fallback: true
  max_retries: 3
  output_format: json
"""

    GENERATOR_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    GENERATOR_CONFIG.write_text(config_content, encoding="utf-8")
    print(f"  [OK]  Generated {GENERATOR_CONFIG}")


def render_template(template_path: Path, env_vars: dict[str, str]) -> str:
    """Render a template file by replacing {{env.VAR_NAME}} placeholders with .env values."""
    if not template_path.exists():
        print(f"  [SKIP] Template not found: {template_path}")
        return ""

    content = template_path.read_text(encoding="utf-8")

    def replace_placeholder(match):
        var_name = match.group(1)
        value = env_vars.get(var_name, "")
        if not value:
            value = match.group(0)
        return value

    rendered = re.sub(r"\{\{env\.(\w+)\}\}", replace_placeholder, content)
    return rendered


def render_example_config(env_vars: dict[str, str]) -> None:
    """Render azure-skill-generator/assets/example-config.yaml with .env values."""
    if not GENERATOR_EXAMPLE_CONFIG.exists():
        print(f"  [SKIP] example-config.yaml not found")
        return

    rendered = render_template(GENERATOR_EXAMPLE_CONFIG, env_vars)
    GENERATOR_EXAMPLE_CONFIG.write_text(rendered, encoding="utf-8")
    print(f"  [OK]  Rendered {GENERATOR_EXAMPLE_CONFIG}")


def print_status(env_vars: dict[str, str]) -> None:
    """Print current environment status."""
    print("\nAzure Environment Status:")
    print("-" * 40)
    for var in REQUIRED_AZURE_VARS + OPTIONAL_AZURE_VARS:
        value = env_vars.get(var, "")
        if value and not value.startswith("your_"):
            masked = value[:4] + "***" if len(value) > 8 else "***"
            print(f"  {var}: {masked}")
        else:
            print(f"  {var}: (not set)")
    print("-" * 40)


def main():
    parser = argparse.ArgumentParser(description="Azure Skills Environment Setup")
    parser.add_argument("--check", action="store_true", help="Only validate .env configuration")
    parser.add_argument("--render", action="store_true", help="Only render config from .env")
    parser.add_argument("--status", action="store_true", help="Show current environment status")
    args = parser.parse_args()

    print("Azure Skills Environment Setup")
    print("=" * 40)

    if args.status:
        env_vars = parse_env_file(ENV_FILE)
        print_status(env_vars)
        return

    if args.check:
        if not ENV_FILE.exists():
            print(f"  [FAIL] .env not found. Run without --check to create it.")
            sys.exit(1)
        env_vars = parse_env_file(ENV_FILE)
        ok = validate_env(env_vars)
        if not ok:
            print("\n  [INFO] Edit .env and fill in your Azure credentials, then re-run.")
            sys.exit(1)
        print("\n  [OK]  All required Azure credentials are set.")
        return

    if args.render:
        if not ENV_FILE.exists():
            print(f"  [FAIL] .env not found. Run without --render to create it first.")
            sys.exit(1)
        env_vars = parse_env_file(ENV_FILE)
        generate_config(env_vars)
        render_example_config(env_vars)
        return

    print("\nStep 1: Initialize .env")
    if not copy_env_example():
        sys.exit(1)

    env_vars = parse_env_file(ENV_FILE)

    print("\nStep 2: Validate credentials")
    validate_env(env_vars)

    print("\nStep 3: Generate skill generator config")
    generate_config(env_vars)

    print("\nStep 4: Render example config")
    render_example_config(env_vars)

    print("\n" + "=" * 40)
    print("Setup complete!")
    print(f"  Config: {GENERATOR_CONFIG}")
    print(f"  Example: {GENERATOR_EXAMPLE_CONFIG}")
    print("\nNext steps:")
    print("  1. Edit .env and fill in your Azure credentials")
    print("  2. Re-run: python azure-skill-generator/scripts/setup_env.py --render")
    print("  3. Use azure-skill-generator to create new skills")


if __name__ == "__main__":
    main()