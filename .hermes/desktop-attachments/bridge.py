"""Crypto relay bridge for Cloudflare Tunnel.

Run:  uv run uvicorn bridge:app --host 127.0.0.1 --port 9999
Tunnel:  cloudflared tunnel --url http://localhost:9999

Endpoints:
- POST /binance/deposit  — Binance SAPI deposit history (internal transfers)
- POST /bsc/rpc          — BNB Chain JSON-RPC proxy (eth_getLogs, etc.)
- GET  /healthz          — liveness
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import time

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET", "")
# ponytail: free official dataseed is rate-limited; set BSC_RPC_URL on the
# bridge box to a premium RPC (Ankr/QuickNode/Nodereal) when throughput matters.
BSC_RPC_URL = os.environ.get("BSC_RPC_URL", "https://bsc-dataseed1.binance.org")
# Fallback mirrors tried in order when the primary rate-limits
_BSC_MIRRORS = [
    "https://bsc-dataseed2.binance.org",
    "https://bsc-dataseed3.binance.org",
    "https://bsc-dataseed1.defibit.io",
    "https://bsc-dataseed1.ninicoin.io",
]

_client = httpx.AsyncClient(timeout=15)


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/bsc/rpc")
async def bsc_rpc(req: Request) -> JSONResponse:
    """Forward a BNB Chain JSON-RPC call to a geo-friendly node.

    Cloud Run (US) cannot reach BSC RPCs directly; this relay runs on a
    non-US box so it can. Body is forwarded verbatim.
    Tries fallback mirrors on rate-limit (-32005).
    """
    try:
        payload = await req.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON-RPC body"}, status_code=400)

    endpoints = [BSC_RPC_URL, *_BSC_MIRRORS]
    last_error: str | None = None
    for endpoint in endpoints:
        try:
            resp = await _client.post(endpoint, json=payload)
            data = resp.json()
            if data.get("error", {}).get("code") == -32005:
                last_error = f"rate-limited on {endpoint}"
                await asyncio.sleep(5)
                continue
            return JSONResponse(data, status_code=resp.status_code)
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            await asyncio.sleep(1)
            continue
    return JSONResponse(
        {"error": f"BSC RPC relay failed on all endpoints. Last error: {last_error}"},
        status_code=502,
    )


@app.post("/binance/deposit")
async def bridge_deposit(req: Request) -> JSONResponse:
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return JSONResponse(
            {"error": "Binance API key not configured"}, status_code=500
        )

    body = await req.json()
    internal_txid = (body.get("internal_txid") or "").strip()
    if not internal_txid:
        return JSONResponse({"error": "Missing internal_txid"}, status_code=400)

    now_ms = int(time.time() * 1000)
    params = {
        "coin": "USDT",
        "status": "1",
        "startTime": str(now_ms - 48 * 3600 * 1000),
        "timestamp": str(now_ms),
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    signature = hmac.new(
        BINANCE_API_SECRET.encode(), query.encode(), hashlib.sha256
    ).hexdigest()

    url = f"https://api.binance.com/sapi/v1/capital/deposit/hisrec?{query}&signature={signature}"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers={"X-MBX-APIKEY": BINANCE_API_KEY})
            status = resp.status_code
            if status != 200:
                return JSONResponse(
                    {"error": f"Binance returned {status}", "detail": resp.text[:500]},
                    status_code=502,
                )
            deposits = resp.json()
            return JSONResponse({"internal_txid": internal_txid, "deposits": deposits})
    except Exception as exc:
        return JSONResponse(
            {"error": f"Bridge call failed: {type(exc).__name__}: {exc}"},
            status_code=502,
        )
