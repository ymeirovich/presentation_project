# src/service/http.py
from __future__ import annotations

import os
import hmac
import hashlib
import pathlib
import time
import logging
import threading
from typing import Optional
from urllib.parse import parse_qs
import threading
import httpx
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from pathlib import Path
import re, json, time
from src.mcp_lab.orchestrator import orchestrate, orchestrate_mixed
from src.common.jsonlog import jlog
from dotenv import load_dotenv
from src.data.ingest import ingest_file
from src.data.catalog import resolve_dataset
from typing import List, Dict, Any

load_dotenv()


log = logging.getLogger("service")

# --- Env & globals ---
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
DEBUG_BYPASS_SLACK_SIG = os.getenv("DEBUG_BYPASS_SLACK_SIG", "0") == "1"

log.info("Slack signing secret loaded? %s", "YES" if SLACK_SIGNING_SECRET else "NO")
if not SLACK_SIGNING_SECRET and not DEBUG_BYPASS_SLACK_SIG:
    log.warning(
        "SLACK_SIGNING_SECRET is not set! Slack verification will fail. "
        "For local testing only, export DEBUG_BYPASS_SLACK_SIG=1."
    )

app = FastAPI()

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3003", "http://localhost:3000"],  # Next.js dev servers
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log incoming request
        jlog(
            log,
            logging.INFO,
            event="http_request_start",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_host=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown"),
        )
        
        try:
            response = await call_next(request)
            
            # Log successful response
            duration = round(time.time() - start_time, 3)
            jlog(
                log,
                logging.INFO,
                event="http_request_complete",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_secs=duration,
            )
            
            return response
            
        except Exception as e:
            # Log failed response
            duration = round(time.time() - start_time, 3)
            jlog(
                log,
                logging.ERROR,
                event="http_request_failed",
                method=request.method,
                path=request.url.path,
                duration_secs=duration,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


app.add_middleware(RequestLoggingMiddleware)


# ---------- Helpers ----------
def verify_slack(req: Request, raw: bytes) -> None:
    """
    Verify Slack signature against the RAW request body (bytes).
    Must be called BEFORE parsing.
    """
    if DEBUG_BYPASS_SLACK_SIG:
        jlog(
            log,
            logging.WARNING,
            event="slack_sig_bypass",
            note="DEBUG_BYPASS_SLACK_SIG=1",
        )
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
    expected = (
        "v0="
        + hmac.new(
            SLACK_SIGNING_SECRET.encode("utf-8"), base, hashlib.sha256
        ).hexdigest()
    )

    # Debug (safe—hash only, no secrets)
    jlog(
        log,
        logging.INFO,
        event="slack_sig_debug",
        header_sig=sig,
        expected_sig=expected,
        ts=ts,
        raw_len=len(raw),
    )

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
            r = httpx.post(
                "https://slack.com/api/chat.postMessage",
                headers=headers,
                json=data,
                timeout=20,
            )
            if not (r.status_code == 200 and r.json().get("ok")):
                jlog(
                    log,
                    logging.WARNING,
                    event="slack_post_warn",
                    status=r.status_code,
                    body=r.text,
                )
                # Try response_url as a fallback
                if response_url:
                    httpx.post(response_url, json={"text": text}, timeout=15)
            return

        # No bot token or no channel? Use response_url if provided
        if response_url:
            httpx.post(response_url, json={"text": text}, timeout=15)
        else:
            jlog(
                log,
                logging.ERROR,
                event="slack_post_error",
                err="No SLACK_BOT_TOKEN/channel_id and no response_url",
            )
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
    start_time = time.time()
    request_info = {
        "request_id": req.request_id,
        "text_length": len(req.report_text) if req.report_text else 0,
        "slides": req.slides,
        "use_cache": req.use_cache,
        "is_file_upload": len(req.report_text) > 10000 if req.report_text else False  # Heuristic for file uploads
    }
    
    jlog(
        log,
        logging.INFO,
        event="render_request_start",
        **request_info
    )
    
    try:
        # Validate report_text is not empty
        if not req.report_text or not req.report_text.strip():
            jlog(log, logging.ERROR, event="render_validation_failed", error="empty_text", **request_info)
            raise HTTPException(status_code=400, detail="report_text cannot be empty")
        
        jlog(log, logging.INFO, event="render_calling_orchestrate", **request_info)
        
        res = orchestrate(
            req.report_text,
            client_request_id=req.request_id,
            use_cache=req.use_cache,
            slide_count=req.slides,
        )
        
        orchestrate_time = time.time()
        jlog(
            log,
            logging.INFO, 
            event="render_orchestrate_complete",
            orchestrate_duration_secs=round(orchestrate_time - start_time, 2),
            result_keys=list(res.keys()) if res else [],
            has_url=bool(res.get("url")),
            **request_info
        )
        
        # Validate response has required fields
        if not res.get("url"):
            jlog(log, logging.ERROR, event="render_no_url", orchestrate_result=res, **request_info)
            raise HTTPException(status_code=500, detail="Presentation was created but no URL returned")
        
        # Build response payload
        response_payload = {
            "ok": True,
            "url": res.get("url"),
            "presentation_id": res.get("presentation_id"),
            "created_slides": res.get("created_slides"),
            "first_slide_id": res.get("first_slide_id"),
        }
        
        total_time = time.time()
        jlog(
            log,
            logging.INFO,
            event="render_success",
            total_duration_secs=round(total_time - start_time, 2),
            url=res.get("url"),
            created_slides=res.get("created_slides"),
            **request_info
        )
        
        return response_payload
        
    except HTTPException as e:
        error_time = time.time()
        jlog(
            log,
            logging.ERROR,
            event="render_http_exception",
            duration_secs=round(error_time - start_time, 2),
            status_code=e.status_code,
            detail=e.detail,
            **request_info
        )
        raise
    except Exception as e:
        error_time = time.time()
        # Enhanced error logging with stack trace and more context
        import traceback
        stack_trace = traceback.format_exc()
        
        jlog(
            log,
            logging.ERROR,
            event="render_exception",
            duration_secs=round(error_time - start_time, 2),
            error=str(e),
            error_type=type(e).__name__,
            error_module=getattr(type(e), '__module__', 'unknown'),
            stack_trace=stack_trace,
            **request_info
        )
        
        # Log additional context based on error type
        if "orchestrate" in str(e).lower() or hasattr(e, '__module__') and 'orchestrator' in str(getattr(e, '__module__', '')):
            jlog(log, logging.ERROR, event="render_orchestrator_error_context", 
                 error=str(e), **request_info)
        elif "slides" in str(e).lower() or "presentation" in str(e).lower():
            jlog(log, logging.ERROR, event="render_slides_error_context", 
                 error=str(e), **request_info)
        elif "timeout" in str(e).lower():
            jlog(log, logging.ERROR, event="render_timeout_error_context", 
                 error=str(e), **request_info)
        
        log.error(f"Render request failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


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
    text = payload.get("text", [""]).strip()

    # persist exactly what Slack sent, for debugging
    dbg = Path("out/state/last_slack_request.json")
    dbg.parent.mkdir(parents=True, exist_ok=True)
    dbg.write_text(
        json.dumps(
            {
                "ts": int(time.time()),
                "raw": raw.decode("utf-8"),
                "payload": {k: v for k, v in payload.items()},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if not text:
        return {
            "response_type": "ephemeral",
            "text": "Please provide some text, e.g. `/presgen Make a 3‑slide overview of PresGen`",
        }

    args = parse_mixed_command(text)
    jlog(
        log,
        logging.INFO,
        event="slack_cmd_parsed",
        text=text,
        slides=args["slides"],
        dataset_hint=args["dataset_hint"],
        sheet=args["sheet"],
        n_questions=len(args["data_questions"]),
    )

    def _run():
        try:
            if args["data_questions"]:
                # Resolve dataset (latest | ds_id | filename)
                ds = resolve_dataset(args["dataset_hint"] or "latest")
                if not ds:
                    _post_followup(
                        channel_id,
                        response_url,
                        "❌ No dataset found. Upload a spreadsheet or specify `data: ds_…`.",
                    )
                    return
                res = orchestrate_mixed(
                    report_text=text,
                    slide_count=args["slides"],
                    dataset_id=ds,
                    data_questions=args["data_questions"],
                    sheet=args["sheet"],
                    use_cache=True,
                )
            else:
                res = orchestrate(
                    text,
                    client_request_id=None,
                    use_cache=True,
                    slide_count=args["slides"],
                )
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
                    "text": f"""*PresGen received your request:*
`/presgen {text}`""",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Working on it… I’ll post the deck link here shortly.",
                    }
                ],
            },
        ],
    }


class DataAsk(BaseModel):
    dataset_id: Optional[str] = None
    dataset_hint: Optional[str] = None  # "latest" | "ds_xxx" | filename
    sheet: Optional[str] = None
    questions: List[str]
    report_text: str = "Data insights"
    slides: int = 1
    use_cache: bool = True


@app.post("/data/ask")
async def data_ask(req: DataAsk):
    start_time = time.time()
    request_info = {
        "dataset_hint": req.dataset_hint,
        "sheet": req.sheet,
        "slides": req.slides,
        "n_questions": len(req.questions),
        "use_cache": req.use_cache
    }
    
    jlog(log, logging.INFO, event="data_ask_start", **request_info)
    
    try:
        ds = req.dataset_id or resolve_dataset(req.dataset_hint or "latest")
        if not ds:
            jlog(log, logging.ERROR, event="data_ask_no_dataset", **request_info)
            raise HTTPException(
                status_code=400,
                detail="No dataset found. Upload a file or specify dataset_id/dataset_hint.",
            )
        
        request_info["dataset_id"] = ds
        jlog(log, logging.INFO, event="data_ask_dataset_resolved", **request_info)
        
        # Call orchestrate_mixed with enhanced error context
        res = orchestrate_mixed(
            req.report_text,
            slide_count=req.slides,
            dataset_id=ds,
            data_questions=req.questions,
            sheet=req.sheet,
            use_cache=req.use_cache,
        )
        
        # Validate response
        if not res.get("url"):
            jlog(log, logging.ERROR, event="data_ask_no_url", 
                 orchestrate_result=res, **request_info)
            raise HTTPException(status_code=500, detail="Presentation was created but no URL returned")
        
        total_time = time.time() - start_time
        jlog(log, logging.INFO, event="data_ask_success", 
             duration_secs=round(total_time, 2),
             created_slides=res.get("created_slides"),
             url=res.get("url"), **request_info)
        
        return {
            "ok": True,
            "url": res.get("url"),
            "dataset_id": ds,
            "created_slides": res.get("created_slides"),
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        import traceback
        error_time = time.time() - start_time
        jlog(log, logging.ERROR, event="data_ask_exception", 
             error=str(e), error_type=type(e).__name__, 
             duration_secs=round(error_time, 2),
             stack_trace=traceback.format_exc(), **request_info)
        log.error(f"Data ask request failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/slack/events")
async def slack_events(request: Request):
    raw = await request.body()
    verify_slack(request, raw)  # reuse your existing signature verifier

    evt = json.loads(raw.decode("utf-8"))
    if "challenge" in evt:  # URL verification
        return {"challenge": evt["challenge"]}

    typ = evt.get("type")
    if typ == "event_callback":
        e = evt.get("event", {})
        if e.get("type") == "file_shared":
            file_id = e.get("file_id") or (e.get("file", {}) or {}).get("id")
            # fetch metadata
            headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
            r = httpx.get(
                "https://slack.com/api/files.info",
                params={"file": file_id},
                headers=headers,
                timeout=20,
            )
            info = r.json()
            if not info.get("ok"):
                jlog(log, logging.WARNING, event="slack_files_info_fail", body=info)
                return {"ok": False}

            fmeta = info["file"]
            url = fmeta["url_private_download"]
            fname = fmeta.get("name", "data.xlsx")
            # download
            raw_dir = pathlib.Path("out/data/tmp")
            raw_dir.mkdir(parents=True, exist_ok=True)
            raw_path = raw_dir / fname
            with httpx.stream("GET", url, headers=headers, timeout=None) as resp:
                resp.raise_for_status()
                with raw_path.open("wb") as out:
                    for chunk in resp.iter_raw():
                        out.write(chunk)

            result = ingest_file(raw_path, original_name=fname)
            # post ack
            channel = e.get("channel") or evt.get("event", {}).get("channel")
            msg = f"📊 Dataset ready: `{result['dataset_id']}` (sheets: {', '.join(result['sheets'])}). Use `data: latest` in `/presgen`."
            _post_followup(channel, None, msg)
            return {"ok": True}

    return {"ok": True}


# --- Slack command mini-grammar parser ---
def parse_mixed_command(text: str) -> dict:
    """
    Understands:
      - slide count: "10-slide", "10 slides", "slides: 10"
      - dataset hint: "data: latest", "data: ds_ab12cd34", "data: sales.xlsx"
      - sheet name: "sheet: Sales2023"
      - questions: "ask: q1; q2; q3"
    Returns: {"slides", "dataset_hint", "sheet", "data_questions"}
    """
    slides = 1
    m = re.search(
        r"(?:(\d+)\s*-\s*slide\b)|(?:\bslides?\s*:\s*(\d+)\b)|(?:\b(\d+)\s*slides?\b)",
        text,
        re.I,
    )
    if m:
        slides = int(next(g for g in m.groups() if g))

    m = re.search(r"\bdata:\s*([A-Za-z0-9._\-]+)\b", text, re.I)
    dataset_hint = m.group(1) if m else None

    m = re.search(r"\bsheet:\s*([A-Za-z0-9 _\-]+)\b", text, re.I)
    sheet = m.group(1).strip() if m else None

    m = re.search(r"\bask:\s*(.+)$", text, re.I | re.S)
    data_questions = [
        q.strip(" \"'\t") for q in (m.group(1).split(";") if m else []) if q.strip()
    ]

    return {
        "slides": slides,
        "dataset_hint": dataset_hint,
        "sheet": sheet,
        "data_questions": data_questions,
    }


@app.post("/data/upload")
async def data_upload(file: UploadFile = File(...)):
    start_time = time.time()
    upload_info = {
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": 0
    }
    
    jlog(log, logging.INFO, event="data_upload_start", **upload_info)
    
    try:
        # Validate file
        if not file.filename:
            jlog(log, logging.ERROR, event="data_upload_no_filename", **upload_info)
            raise HTTPException(status_code=400, detail="No filename provided")
            
        raw_dir = pathlib.Path("out/data/tmp")
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / file.filename
        
        # Read and save file
        file_content = await file.read()
        upload_info["size_bytes"] = len(file_content)
        
        jlog(log, logging.INFO, event="data_upload_file_read", **upload_info)
        
        with raw_path.open("wb") as f:
            f.write(file_content)
            
        jlog(log, logging.INFO, event="data_upload_file_saved", 
             path=str(raw_path), **upload_info)
        
        # Process file
        info = ingest_file(raw_path, original_name=file.filename)
        
        total_time = time.time() - start_time
        jlog(log, logging.INFO, event="data_upload_success", 
             duration_secs=round(total_time, 2), 
             dataset_id=info.get("dataset_id"), 
             sheets=info.get("sheets", []), **upload_info)
        
        return info
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        import traceback
        error_time = time.time() - start_time
        jlog(log, logging.ERROR, event="data_upload_exception", 
             error=str(e), error_type=type(e).__name__, 
             duration_secs=round(error_time, 2),
             stack_trace=traceback.format_exc(), **upload_info)
        log.error(f"Data upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
