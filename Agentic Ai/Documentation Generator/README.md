## Development setup with uv (Windows PowerShell)

This project uses a local virtual environment and the uv package manager for fast, reproducible installs.

### One-time setup and activation

Run the setup script and dot-source it to activate the environment in your current shell:

```powershell
# From the project root
. .\scripts\setup-uv.ps1
```

What this does:
- Installs uv if missing
- Creates .venv (Python 3.11) if missing
- Installs dependencies from pyproject.toml (or requirements.txt if no pyproject)
- Activates the .venv in your current terminal

VS Code is configured to auto-activate the local interpreter via `.vscode/settings.json`.

### Installing new packages

Prefer editing `pyproject.toml` and then syncing:

```powershell
# After adding a dependency to pyproject.toml
uv sync
```

Or install ad-hoc into the active env:

```powershell
uv pip install <package>
```

### Running scripts

With the environment active:

```powershell
python .\test.py
```

Alternatively, without activating, you can use uv run (ephemeral activation):

```powershell
uv run python .\test.py
```

