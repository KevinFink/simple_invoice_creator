#!/usr/bin/env python3
"""
Store and retrieve invoice configs in 1Password, with optional local YAML profiles.

Usage:
    # Store a config in 1Password (flags override YAML profile values):
    uv run 1password_config.py store --vault Private --title invoice-config
    uv run 1password_config.py store --vault Private --title invoice-config --account my.1password.com

    # Retrieve a config from 1Password and write it to a local file:
    uv run 1password_config.py retrieve --vault Private --title invoice-config --output config.toml

    # Save connection details as a named YAML profile:
    uv run 1password_config.py save-profile myprofile --vault Private --title invoice-config --account my.1password.com

    # Store/retrieve using a saved profile:
    uv run 1password_config.py store --profile myprofile
    uv run 1password_config.py retrieve --profile myprofile --output config.toml
"""

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

DEFAULT_PROFILES_PATH = Path(__file__).parent / "1password_profiles.yaml"
DEFAULT_CONFIG_PATH = "config.toml"
DEFAULT_TITLE = "invoice-config"


# ---------------------------------------------------------------------------
# YAML profile helpers
# ---------------------------------------------------------------------------

def load_profiles(profiles_path: Path) -> dict:
    if not profiles_path.exists():
        return {}
    return yaml.safe_load(profiles_path.read_text()) or {}


def save_profiles(profiles: dict, profiles_path: Path) -> None:
    profiles_path.write_text(yaml.dump(profiles, default_flow_style=False, sort_keys=False))


def resolve_profile(args: argparse.Namespace, profiles_path: Path) -> dict:
    """Merge a named profile (if any) with explicit CLI flags (flags win)."""
    profile: dict = {}
    if args.profile:
        profiles = load_profiles(profiles_path)
        if args.profile not in profiles:
            print(f"Error: Profile '{args.profile}' not found in {profiles_path}", file=sys.stderr)
            sys.exit(1)
        profile = profiles[args.profile]

    return {
        "vault": args.vault or profile.get("vault"),
        "title": args.title or profile.get("title") or DEFAULT_TITLE,
        "account": args.account or profile.get("account"),
        "config_path": args.config or profile.get("config_path") or DEFAULT_CONFIG_PATH,
    }


# ---------------------------------------------------------------------------
# 1Password helpers
# ---------------------------------------------------------------------------

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


def retrieve_config(vault: str, title: str, account: str | None = None) -> str:
    item_ref = f"op://{vault}/{title}/config"
    cmd = ["op", "read", item_ref]
    if account:
        cmd.extend(["--account", account])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Failed to read from 1Password: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("1Password CLI (op) not found. Install it from https://1password.com/downloads/command-line/", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_store(args: argparse.Namespace) -> None:
    resolved = resolve_profile(args, DEFAULT_PROFILES_PATH)
    vault = resolved["vault"]
    if not vault:
        print("Error: --vault is required (or use --profile)", file=sys.stderr)
        sys.exit(1)

    config_path = Path(resolved["config_path"])
    ref = store_config(config_path, vault, resolved["title"], resolved["account"])

    account_flag = f" --op-account {resolved['account']}" if resolved["account"] else ""
    print(f"\nUse with: uv run create_invoice.py --hours 100 --op-item \"{ref}\"{account_flag}")


def cmd_retrieve(args: argparse.Namespace) -> None:
    resolved = resolve_profile(args, DEFAULT_PROFILES_PATH)
    vault = resolved["vault"]
    if not vault:
        print("Error: --vault is required (or use --profile)", file=sys.stderr)
        sys.exit(1)

    content = retrieve_config(vault, resolved["title"], resolved["account"])
    output_path = Path(args.output) if args.output else Path(resolved["config_path"])
    output_path.write_text(content)
    print(f"Config written to {output_path}")


def cmd_save_profile(args: argparse.Namespace) -> None:
    if not args.vault:
        print("Error: --vault is required when saving a profile", file=sys.stderr)
        sys.exit(1)

    profiles = load_profiles(DEFAULT_PROFILES_PATH)
    profile_data: dict[str, str] = {"vault": args.vault}
    if args.title:
        profile_data["title"] = args.title
    if args.account:
        profile_data["account"] = args.account
    if args.config and args.config != DEFAULT_CONFIG_PATH:
        profile_data["config_path"] = args.config

    profiles[args.profile_name] = profile_data
    save_profiles(profiles, DEFAULT_PROFILES_PATH)
    print(f"Profile '{args.profile_name}' saved to {DEFAULT_PROFILES_PATH}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Store, retrieve, and manage invoice configs with 1Password",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # shared flags --------------------------------------------------------
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--vault", type=str, help="1Password vault name")
    common.add_argument("--title", type=str, help=f"Item title in 1Password (default: {DEFAULT_TITLE})")
    common.add_argument("--account", type=str, help="1Password account (e.g. 'my.1password.com')")
    common.add_argument("--config", type=str, help=f"Path to config file (default: {DEFAULT_CONFIG_PATH})")
    common.add_argument("--profile", type=str, help="Named profile from 1password_profiles.yaml")

    # store ---------------------------------------------------------------
    subparsers.add_parser("store", parents=[common], help="Store a config file in 1Password")

    # retrieve ------------------------------------------------------------
    p_retrieve = subparsers.add_parser("retrieve", parents=[common], help="Retrieve a config from 1Password")
    p_retrieve.add_argument("--output", type=str, help="Output file path (default: value of --config)")

    # save-profile --------------------------------------------------------
    p_profile = subparsers.add_parser(
        "save-profile", parents=[common],
        help="Save 1Password connection details as a named profile",
    )
    p_profile.add_argument("profile_name", help="Name for the profile")

    args = parser.parse_args()

    match args.command:
        case "store":
            cmd_store(args)
        case "retrieve":
            cmd_retrieve(args)
        case "save-profile":
            cmd_save_profile(args)


if __name__ == "__main__":
    main()
