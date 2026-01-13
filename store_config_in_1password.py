#!/usr/bin/env python3
"""
Store config.toml in 1Password.

Usage:
    uv run store_config_in_1password.py --vault Private --title invoice-config
    uv run store_config_in_1password.py --vault Private --title invoice-config --account my.1password.com
"""

import argparse
import subprocess
import sys
from pathlib import Path


def item_exists(vault: str, title: str, account: str | None = None) -> bool:
    cmd = ["op", "item", "get", title, "--vault", vault]
    if account:
        cmd.extend(["--account", account])
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def store_config(config_path: Path, vault: str, title: str, account: str | None = None) -> str:
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    config_content = config_path.read_text()
    account_args = ["--account", account] if account else []

    try:
        if item_exists(vault, title, account):
            cmd = [
                "op", "item", "edit", title,
                "--vault", vault,
                f"config[text]={config_content}",
                *account_args,
            ]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"Config updated in 1Password: op://{vault}/{title}/config")
        else:
            cmd = [
                "op", "item", "create",
                "--category", "Secure Note",
                "--vault", vault,
                "--title", title,
                f"config[text]={config_content}",
                *account_args,
            ]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"Config stored in 1Password: op://{vault}/{title}/config")
        return f"op://{vault}/{title}/config"
    except subprocess.CalledProcessError as e:
        print(f"Failed to store in 1Password: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("1Password CLI (op) not found. Install it from https://1password.com/downloads/command-line/", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Store config.toml in 1Password")
    parser.add_argument("--config", type=str, default="config.toml",
                        help="Path to config file (default: config.toml)")
    parser.add_argument("--vault", type=str, required=True,
                        help="1Password vault name")
    parser.add_argument("--title", type=str, default="invoice-config",
                        help="Item title in 1Password (default: invoice-config)")
    parser.add_argument("--account", type=str,
                        help="1Password account (e.g., 'my.1password.com')")
    args = parser.parse_args()

    config_path = Path(args.config)
    ref = store_config(config_path, args.vault, args.title, args.account)

    account_flag = f" --op-account {args.account}" if args.account else ""
    print(f"\nUse with: uv run create_invoice.py --hours 100 --op-item \"{ref}\"{account_flag}")


if __name__ == "__main__":
    main()
