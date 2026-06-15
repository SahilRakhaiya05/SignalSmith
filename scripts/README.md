# Scripts

Essential project scripts only.

| Script | Platform | Purpose |
|--------|----------|---------|
| `setup.ps1` | Windows | Install Python + npm deps, create `.env` |
| `setup.sh` | Linux/macOS | Same as setup.ps1 |
| `install_mcp.ps1` | Windows | Install Splunk MCP Server (Splunkbase 7931) |
| `start.ps1` | Windows | Build frontend + start API/UI on port 8080 |
| `start.sh` | Linux/macOS | Same as start.ps1 |

## Usage

**Windows:**

```powershell
.\scripts\setup.ps1
.\scripts\install_mcp.ps1
.\scripts\start.ps1
```

**Linux / macOS:**

```bash
./scripts/setup.sh
./scripts/start.sh
```

Open **http://localhost:8080** and run the pipeline from the UI.

Utility scripts for development live in `backend/scripts/` (MCP check, Splunk verify, etc.).