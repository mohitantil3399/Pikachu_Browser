#!/usr/bin/env python3
"""
Pikachu AI Browser — Automated 1-Click Setup Runner
Reads 'setup.yaml' and provisions all dependencies, environment,
TypeScript bundle, and SearXNG Docker container in one step.
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
YAML_SPEC = ROOT_DIR / "setup.yaml"


def print_banner():
    print("=" * 60)
    print(" ⚡ Pikachu Browser — 1-Click Automated Setup Runner")
    print("=" * 60)


def run_command(cmd, check=True, cwd=ROOT_DIR):
    print(f"  [EXEC] {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    return subprocess.run(cmd, shell=isinstance(cmd, str), check=check, cwd=cwd)


def step_check_prerequisites():
    print("\n[Step 1/5] Checking System Prerequisites...")
    # Python version
    major, minor = sys.version_info.major, sys.version_info.minor
    if major < 3 or (major == 3 and minor < 10):
        print(f"  [-] Error: Python 3.10+ required. Found Python {major}.{minor}")
        sys.exit(1)
    print(f"  [+] Python version: {major}.{minor}.{sys.version_info.micro} (OK)")

    # Node.js
    node_path = shutil.which("node")
    if node_path:
        res = subprocess.run(["node", "--version"], capture_output=True, text=True)
        print(f"  [+] Node.js: {res.stdout.strip()} (OK)")
    else:
        print("  [!] Warning: 'node' not found on PATH. TypeScript auto-build may need manual invocation.")

    # Docker
    docker_path = shutil.which("docker")
    if docker_path:
        res = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        print(f"  [+] Docker: {res.stdout.strip()} (OK)")
    else:
        print("  [!] Warning: 'docker' not found on PATH. Local SearXNG container requires Docker Desktop.")


def step_install_dependencies():
    print("\n[Step 2/5] Installing Python Dependencies...")
    req_file = ROOT_DIR / "requirements.txt"
    if req_file.exists():
        run_command([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
    else:
        print("  [-] requirements.txt not found, skipping.")


def step_setup_env():
    print("\n[Step 3/5] Setting up Environment Configuration (.env)...")
    env_file = ROOT_DIR / ".env"
    example_file = ROOT_DIR / ".env.example"

    if not env_file.exists() and example_file.exists():
        shutil.copy(example_file, env_file)
        print(f"  [+] Created '{env_file.name}' from template.")
    else:
        print(f"  [+] Found '{env_file.name}'.")

    # Interactive / Guided walk-through
    print("\n  --- 🔑 Environment Key Setup Guide ---")
    print("  Pikachu Browser works out-of-the-box for ad-free browsing with local defaults.")
    print("  To activate the AI research assistant and live intelligence, obtain free API keys:\n")

    keys_guide = [
        ("GROQ_API_KEY", "Groq Cloud (Recommended: free ultra-fast Llama-3)", "https://console.groq.com/keys"),
        ("TAVILY_API_KEY", "Tavily Search (Automated cloud backup for SearXNG)", "https://app.tavily.com/sign-in"),
        ("MISTRAL_API_KEY", "Mistral AI (Codestral & Mistral Large reasoning)", "https://console.mistral.ai/api-keys/"),
        ("OPENROUTER_API_KEY", "OpenRouter (Aggregated access to 100+ models)", "https://openrouter.ai/keys"),
        ("WEATHER_API_KEY", "OpenWeatherMap (Live civic weather intelligence)", "https://home.openweathermap.org/api_keys"),
    ]

    for key, desc, link in keys_guide:
        print(f"    • {key:<18} : {desc}")
        print(f"      Get free key    : {link}")

    print("\n  Local SearXNG endpoint is configured to: http://localhost:8888/search")
    print("  You can open and update '.env' anytime with your preferred editor.")


def step_build_typescript_shield():
    print("\n[Step 4/5] Building TypeScript Privacy Shield...")
    build_script = ROOT_DIR / "src" / "scripts" / "build.mjs"
    bundle_file = ROOT_DIR / "src" / "scripts" / "privacy_shield.bundle.js"

    if build_script.exists():
        try:
            run_command(["node", str(build_script)])
            print("  [+] TypeScript Privacy Shield compiled successfully.")
        except Exception as e:
            if bundle_file.exists():
                print(f"  [!] Rebuild note: Using existing bundle ({bundle_file.name}).")
            else:
                print(f"  [-] Build error: {e}")
    elif bundle_file.exists():
        print(f"  [+] Using pre-compiled production bundle ({bundle_file.name}).")


def step_check_searxng_container():
    print("\n[Step 5/5] Checking Local SearXNG Docker Container...")
    try:
        # Check if searxng is already running
        res = subprocess.run(
            ["docker", "ps", "--filter", "name=searxng", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )
        if "searxng" in res.stdout:
            print("  [+] SearXNG Docker container is already running on port 8888.")
            return

        # Check if stopped container exists
        res_all = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=searxng", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )
        if "searxng" in res_all.stdout:
            print("  [*] Starting stopped 'searxng' container...")
            run_command(["docker", "start", "searxng"])
        else:
            print("  [*] Starting new 'searxng' container on port 8888...")
            settings_path = str(ROOT_DIR / "settings.yml")
            cmd = [
                "docker", "run", "-d",
                "-p", "8888:8080",
                "-v", f"{settings_path}:/etc/searxng/settings.yml",
                "--name", "searxng",
                "searxng/searxng"
            ]
            run_command(cmd)

        print("  [+] SearXNG container launched.")
    except Exception as e:
        print(f"  [!] Note on Docker: {e}")
        print("      Browser will automatically failover to Tavily Search if Docker is inactive.")


def main():
    print_banner()
    step_check_prerequisites()
    step_install_dependencies()
    step_setup_env()
    step_build_typescript_shield()
    step_check_searxng_container()

    print("\n" + "=" * 60)
    print(" ✅ Setup complete! You can now start Pikachu Browser with:")
    print("    python app.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
