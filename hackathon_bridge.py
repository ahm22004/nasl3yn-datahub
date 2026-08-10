"""
Hackathon Discovery API Bridge — Public API wrapper for scanner with Cloudflare Tunnel.

Run:  uv run uvicorn hackathon_bridge:app --host 127.0.0.1 --port 8888
Tunnel:  cloudflared tunnel --url http://localhost:8888

Endpoints:
- GET  /healthz                    — Liveness
- GET  /scan                       — Trigger scan, return latest report
- GET  /report                     — Latest markdown report
- GET  /report/json                — Latest report as JSON
- GET  /sources                    — Source status/health
- POST /scan/force                 — Force immediate scan (bypass cache)

Config via env:
- HACKATHON_SCRAPER_PROXY          — HTTP proxy for blocked sources
- SCAN_CACHE_TTL_SECONDS           — Cache TTL (default: 3600)
- CLOUDFLARE_TUNNEL_TOKEN          — For managed tunnel (optional)
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

app = FastAPI(title="Hackathon Discovery Bridge", version="1.0.0")

# Config
REPORTS_DIR = Path.home() / ".hermes" / "reports" / "hackathons"
SCANNER_SCRIPT = Path.home() / ".hermes" / "scripts" / "hackathon_weekly.py"
CACHE_TTL = int(os.environ.get("SCAN_CACHE_TTL_SECONDS", "3600"))
PROXY = os.environ.get("HACKATHON_SCRAPER_PROXY")

# State
_last_scan_time = 0
_last_report_path: Path | None = None
_scan_lock = asyncio.Lock()
_source_stats: dict[str, dict] = {}

# HTTP client with proxy support
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        proxy = PROXY
        _client = httpx.AsyncClient(
            timeout=30,
            proxy=proxy,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
    return _client


@app.on_event("shutdown")
async def shutdown():
    global _client
    if _client:
        await _client.aclose()


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    """Liveness probe."""
    return {
        "ok": True,
        "service": "hackathon-discovery-bridge",
        "version": "1.0.0",
        "cache_ttl": CACHE_TTL,
        "proxy_configured": bool(PROXY),
    }


@app.get("/sources")
async def sources() -> dict[str, Any]:
    """Source health status."""
    return {
        "sources": _source_stats,
        "last_scan": _last_scan_time,
        "cache_ttl_seconds": CACHE_TTL,
    }


def _find_latest_report() -> Path | None:
    """Find most recent report file."""
    if not REPORTS_DIR.exists():
        return None
    reports = list(REPORTS_DIR.glob("hackathon_report_*.md"))
    if not reports:
        return None
    return max(reports, key=lambda p: p.stat().st_mtime)


def _find_latest_jsonl() -> Path | None:
    """Find most recent JSONL log."""
    if not REPORTS_DIR.exists():
        return None
    logs = list(REPORTS_DIR.glob("hackathon_log.jsonl"))
    return logs[0] if logs else None


async def _run_scan(force: bool = False) -> Path:
    """Run the scanner script, return report path."""
    global _last_scan_time, _last_report_path, _source_stats

    async with _scan_lock:
        # Check cache
        if not force and _last_report_path and _last_report_path.exists():
            age = time.time() - _last_report_path.stat().st_mtime
            if age < CACHE_TTL:
                return _last_report_path

        # Run scanner
        env = os.environ.copy()
        if PROXY:
            env["HACKATHON_SCRAPER_PROXY"] = PROXY

        proc = await asyncio.create_subprocess_exec(
            "python3", str(SCANNER_SCRIPT), "--limit", "30",
            "--out-dir", str(REPORTS_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"Scanner failed: {stderr.decode()[:500]}")

        # Update stats from stderr
        for line in stderr.decode().splitlines():
            if line.startswith("[discover]") or line.startswith("[search]"):
                parts = line.split()
                if len(parts) >= 3:
                    source = parts[1].strip("[]")
                    status = "ok" if "blocked" not in line else "blocked"
                    _source_stats[source] = {"status": status, "last_seen": time.time()}

        _last_scan_time = time.time()
        _last_report_path = _find_latest_report()
        return _last_report_path or REPORTS_DIR / "hackathon_report_latest.md"


@app.get("/scan")
async def scan(background_tasks: BackgroundTasks, force: bool = False) -> dict[str, Any]:
    """Trigger scan, return latest report metadata."""
    report_path = await _run_scan(force=force)
    report = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    return {
        "report_path": str(report_path),
        "generated_at": _last_scan_time,
        "cache_hit": not force and _last_report_path == report_path,
        "hackathons_found": report.count("## "),
        "preview": report[:500] + "..." if len(report) > 500 else report,
    }


@app.post("/scan/force")
async def scan_force(background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Force immediate scan bypassing cache."""
    return await scan(background_tasks, force=True)


@app.get("/report", response_class=PlainTextResponse)
async def report(force: bool = False) -> str:
    """Latest markdown report."""
    report_path = await _run_scan(force=force)
    return report_path.read_text(encoding="utf-8") if report_path.exists() else "No report yet"


@app.get("/report/json")
async def report_json(force: bool = False) -> JSONResponse:
    """Latest report as structured JSON."""
    report_path = await _run_scan(force=force)
    jsonl_path = _find_latest_jsonl()

    hackathons = []
    if jsonl_path and jsonl_path.exists():
        for line in jsonl_path.read_text().strip().splitlines():
            try:
                hackathons.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    return JSONResponse({
        "generated_at": _last_scan_time,
        "report_path": str(report_path),
        "hackathons": hackathons,
        "count": len(hackathons),
        "source_stats": _source_stats,
    })


# --- Cloudflare Tunnel Management ---

@app.get("/tunnel/status")
async def tunnel_status() -> dict[str, Any]:
    """Check cloudflared status."""
    try:
        result = subprocess.run(
            ["cloudflared", "tunnel", "list"],
            capture_output=True, text=True, timeout=10
        )
        return {"running": result.returncode == 0, "output": result.stdout}
    except FileNotFoundError:
        return {"running": False, "error": "cloudflared not installed"}
    except Exception as e:
        return {"running": False, "error": str(e)}


@app.post("/tunnel/start")
async def tunnel_start(background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Start cloudflared tunnel in background."""
    token = os.environ.get("CLOUDFLARE_TUNNEL_TOKEN")
    if not token:
        raise HTTPException(400, "CLOUDFLARE_TUNNEL_TOKEN not set")

    def run_tunnel():
        subprocess.run(
            ["cloudflared", "tunnel", "run", "--token", token],
            capture_output=True
        )

    background_tasks.add_task(run_tunnel)
    return {"started": True, "message": "Tunnel starting in background"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8888)