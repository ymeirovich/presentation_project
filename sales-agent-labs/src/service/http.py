# src/service/http.py
from __future__ import annotations

import os
import hmac
import hashlib
import time
import logging
import threading
from typing import Optional
from urllib.parse import parse_qs
import threading
import httpx
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from pathlib import Path                 
import re                                
import json                               
import time 
from src.mcp_lab.orchestrator import orchestrate
from src.common.jsonlog import jlog
from dotenv import load_dotenv
load_dotenv()


log = logging.getLogger("service")

# --- Env & globals ---
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
DEBUG_BYPASS_SLACK_SIG = os.getenv("DEBUG_BYPASS_SLACK_SIG", "0") == "1"

log.info("Slack signing secret loaded? %s", "YES" if SLACK_SIGNING_SECRET else "NO")
if not SLACK_SIGNING_SECRET and not DEBUG_BYPASS_SLACK_SIG:
    log.warning("SLACK_SIGNING_SECRET is not set! Slack verification will fail. "
                "For local testing only, export DEBUG_BYPASS_SLACK_SIG=1.")

app = FastAPI()


# ---------- Helpers ----------
def verify_slack(req: Request, raw: bytes) -> None:
    """
    Verify Slack signature against the RAW request body (bytes).
    Must be called BEFORE parsing.
    """
    if DEBUG_BYPASS_SLACK_SIG:
        jlog(log, logging.WARNING, event="slack_sig_bypass", note="DEBUG_BYPASS_SLACK_SIG=1")
        return

    ts = req.headers.get("X-Slack-Request-Timestamp")
    sig = req.headers.get("X-Slack-Signature")
    if not ts or not sig:
        raise HTTPException(status_code=401, detail="Missing Slack headers")

    # Reject very old requests (> 5 minutes)
    try:
        if abs(time.time() - int(ts)) > 300:
            raise HTTPException(status_code=401, detail="Stale Slack request")
    except ValueError:
        raise HTTPException(status_code=401, detail="Bad timestamp")

    # Compute expected signature exactly as Slack specifies: v0:timestamp:raw_body
    base = b"v0:" + ts.encode("utf-8") + b":" + raw
    expected = "v0=" + hmac.new(SLACK_SIGNING_SECRET.encode("utf-8"), base, hashlib.sha256).hexdigest()

    # Debug (safe—hash only, no secrets)
    jlog(log, logging.INFO, event="slack_sig_debug",
         header_sig=sig, expected_sig=expected, ts=ts, raw_len=len(raw))

    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=401, detail="Bad Slack signature")


def _post_followup(channel_id: str, response_url: Optional[str], text: str) -> None:
    """
    Post the result message. Prefer chat.postMessage if we have a bot token and channel,
    otherwise fall back to the response_url (works even if the bot isn't invited).
    """
    try:
        if SLACK_BOT_TOKEN and channel_id:
            headers = {
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json; charset=utf-8",
            }
            data = {"channel": channel_id, "text": text}
            r = httpx.post("https://slack.com/api/chat.postMessage", headers=headers, json=data, timeout=20)
            if not (r.status_code == 200 and r.json().get("ok")):
                jlog(log, logging.WARNING, event="slack_post_warn",
                     status=r.status_code, body=r.text)
                # Try response_url as a fallback
                if response_url:
                    httpx.post(response_url, json={"text": text}, timeout=15)
            return

        # No bot token or no channel? Use response_url if provided
        if response_url:
            httpx.post(response_url, json={"text": text}, timeout=15)
        else:
            jlog(log, logging.ERROR, event="slack_post_error",
                 err="No SLACK_BOT_TOKEN/channel_id and no response_url")
    except Exception as e:
        jlog(log, logging.ERROR, event="slack_post_exception", err=str(e))


# ---------- Models ----------
class RenderRequest(BaseModel):
    report_text: str
    request_id: Optional[str] = None
    slides: int = 1
    use_cache: bool = True
    channel_id: Optional[str] = None  # not used by /render, but kept for compatibility


# ---------- Routes ----------
@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/render")
async def render(req: RenderRequest):
    res = orchestrate(req.report_text,
                      client_request_id=req.request_id,
                      use_cache=req.use_cache,
                      slide_count=req.slides)              # <-- CHANGED
    return {"ok": True, "url": res.get("url")}


@app.post("/slack/command")
async def slack_command(request: Request):
    """
    Slash command handler that:
    - Verifies Slack signature on the RAW body
    - Returns an *ephemeral* ack so the original `/presgen ...` remains visible
    - Does the heavy work in a background thread
    - Posts the final deck link back to the channel (or via response_url)
    """
    raw = await request.body()
    verify_slack(request, raw)  # MUST verify before parsing

    payload = parse_qs(raw.decode("utf-8"))
    user_id = payload.get("user_id", ["unknown"])[0]
    channel_id = payload.get("channel_id", [""])[0]
    response_url = payload.get("response_url", [None])[0]

    # define text BEFORE using it
    text = payload.get("text", [""])[0]
    text = (text or "").strip()

    # persist exactly what Slack sent, for debugging
    dbg = Path("out/state/last_slack_request.json")
    dbg.parent.mkdir(parents=True, exist_ok=True)
    dbg.write_text(json.dumps({
        "ts": int(time.time()),
        "raw": raw.decode("utf-8"),
        "payload": {k: v for k, v in payload.items()},
    }, indent=2), encoding="utf-8")

    if not text:
        return {
            "response_type": "ephemeral",
            "text": "Please provide some text, e.g. `/presgen Make a 3‑slide overview of PresGen`",
        }

    # --- parse '10-slide' or '10 slides' from the text ---
    slides = 1
    m = re.search(r"(?:\b(\d+)\s*-\s*slide\b)|(?:\b(\d+)\s*slides?\b)", text, re.I)
    if m:
        slides = int(next(g for g in m.groups() if g))

    jlog(log, logging.INFO, event="slack_request_parsed",
         user_id=user_id, channel_id=channel_id, text=text, slides=slides)
    #---


    user_id = payload.get("user_id", ["unknown"])[0]
    channel_id = payload.get("channel_id", [""])[0]
    text = payload.get("text", [""])[0].strip()
    response_url = payload.get("response_url", [None])[0]

    if not text:
        return {
            "response_type": "ephemeral",
            "text": "Please provide some text, e.g. `/presgen Make a 3‑slide overview of PresGen`",
        }

    def _run():
        try:
            res = orchestrate(text, client_request_id=None, use_cache=True, slide_count=slides)  # <-- CHANGED
            url = res.get("url") or "(no URL)"
            msg = f"✅ Deck ready for <@{user_id}>: {url}"
        except Exception as e:
            msg = f"❌ Failed to generate deck for <@{user_id}>: {e}"
        _post_followup(channel_id, response_url, msg)


    threading.Thread(target=_run, daemon=True).start()

    # EPHEMERAL ACK (does NOT replace the original slash command message)
    return {
        "response_type": "ephemeral",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*PresGen received your request:*\n`/presgen " + text + "`",
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "Working on it… I’ll post the deck link here shortly."}
                ],
            },
        ],
    }
