# src/service/http.py
from __future__ import annotations

import os
import hmac
import hashlib
import pathlib
import time
import logging
import threading
import uuid
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
import asyncio

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


# Video Processing Models
class VideoUploadResponse(BaseModel):
    job_id: str
    status: str
    message: str
    upload_time: float


class VideoJobStatus(BaseModel):
    job_id: str
    status: str
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float
    updated_at: float


class VideoProcessingResult(BaseModel):
    job_id: str
    status: str
    download_url: Optional[str] = None
    processing_time: Optional[float] = None
    phases: Optional[Dict[str, float]] = None


# ---------- Video Processing Routes ----------

# Global job storage (in production, use Redis or database)
video_jobs: Dict[str, Dict[str, Any]] = {}

def create_video_job(job_id: str, video_path: str) -> Dict[str, Any]:
    """Create a new video processing job"""
    job = {
        "job_id": job_id,
        "status": "uploaded",
        "video_path": video_path,
        "created_at": time.time(),
        "updated_at": time.time(),
        "progress": {},
        "error": None,
        "phases": {}
    }
    video_jobs[job_id] = job
    return job

def update_video_job(job_id: str, **updates) -> Dict[str, Any]:
    """Update video job with new data"""
    if job_id not in video_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = video_jobs[job_id]
    job.update(updates)
    job["updated_at"] = time.time()
    
    jlog(log, logging.INFO, 
         event="video_job_updated",
         job_id=job_id,
         status=job.get("status"),
         updates=list(updates.keys()))
    
    return job

@app.post("/video/upload", response_model=VideoUploadResponse)
async def video_upload(file: UploadFile = File(...)):
    """Upload video file for processing"""
    start_time = time.time()
    job_id = str(uuid.uuid4())
    
    upload_info = {
        "job_id": job_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": 0
    }
    
    jlog(log, logging.INFO, event="video_upload_start", **upload_info)
    
    try:
        # Validate file
        if not file.filename:
            jlog(log, logging.ERROR, event="video_upload_no_filename", **upload_info)
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file extension
        valid_extensions = {'.mp4', '.mov', '.avi', '.mkv'}
        file_ext = pathlib.Path(file.filename).suffix.lower()
        if file_ext not in valid_extensions:
            jlog(log, logging.ERROR, event="video_upload_invalid_format", 
                 extension=file_ext, **upload_info)
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported video format: {file_ext}. Supported: {', '.join(valid_extensions)}"
            )
        
        # Create job directory
        job_dir = pathlib.Path(f"/tmp/jobs/{job_id}")
        job_dir.mkdir(parents=True, exist_ok=True)
        video_path = job_dir / "raw_video.mp4"
        
        # Read and save file
        file_content = await file.read()
        upload_info["size_bytes"] = len(file_content)
        
        # Check file size (max 200MB as per PRD)
        max_size = 200 * 1024 * 1024  # 200MB
        if upload_info["size_bytes"] > max_size:
            jlog(log, logging.ERROR, event="video_upload_too_large", **upload_info)
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {upload_info['size_bytes']/1024/1024:.1f}MB. Max: 200MB"
            )
        
        jlog(log, logging.INFO, event="video_upload_file_read", **upload_info)
        
        # Save video file
        with video_path.open("wb") as f:
            f.write(file_content)
        
        # Create job record
        job = create_video_job(job_id, str(video_path))
        
        upload_time = time.time() - start_time
        
        jlog(log, logging.INFO, event="video_upload_success", 
             duration_secs=round(upload_time, 2), 
             job_path=str(video_path), **upload_info)
        
        return VideoUploadResponse(
            job_id=job_id,
            status="uploaded",
            message="Video uploaded successfully. Ready for processing.",
            upload_time=upload_time
        )
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        import traceback
        error_time = time.time() - start_time
        jlog(log, logging.ERROR, event="video_upload_exception", 
             error=str(e), error_type=type(e).__name__, 
             duration_secs=round(error_time, 2),
             stack_trace=traceback.format_exc(), **upload_info)
        log.error(f"Video upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Video upload failed: {str(e)}")

@app.get("/video/status/{job_id}", response_model=VideoJobStatus)
async def video_status(job_id: str):
    """Get video processing job status"""
    if job_id not in video_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = video_jobs[job_id]
    
    return VideoJobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress"),
        error=job.get("error"),
        created_at=job["created_at"],
        updated_at=job["updated_at"]
    )

@app.post("/video/process/{job_id}")
async def video_process(job_id: str):
    """Start video processing with Phase 1 parallel agents"""
    if job_id not in video_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = video_jobs[job_id]
    if job["status"] != "uploaded":
        raise HTTPException(
            status_code=400, 
            detail=f"Job {job_id} is not ready for processing. Status: {job['status']}"
        )
    
    # Update job status to processing
    update_video_job(job_id, status="processing", progress={"phase": "starting"})
    
    jlog(log, logging.INFO, event="video_processing_started", job_id=job_id)
    
    try:
        # Import and initialize parallel orchestrator
        from src.mcp.tools.video_orchestrator import ParallelVideoOrchestrator
        
        orchestrator = ParallelVideoOrchestrator(job_id)
        
        # Execute Phase 1 parallel processing
        jlog(log, logging.INFO, event="phase1_starting", job_id=job_id)
        update_video_job(job_id, progress={"phase": "phase1", "status": "processing"})
        
        result = await orchestrator.phase1_parallel_processing(job["video_path"])
        
        if result.success:
            # Update job with Phase 1 results
            update_video_job(
                job_id,
                status="phase1_complete",
                progress={
                    "phase": "phase1_complete",
                    "processing_time": result.processing_time,
                    "audio_success": result.audio_result.success,
                    "video_success": result.video_result.success,
                    "audio_duration": result.audio_result.duration,
                    "video_confidence": result.video_result.confidence_score
                },
                phases={"phase1": result.processing_time}
            )
            
            jlog(log, logging.INFO, 
                 event="phase1_success",
                 job_id=job_id,
                 processing_time=result.processing_time,
                 target_met=result.processing_time < 30)
            
            return {
                "job_id": job_id,
                "status": "phase1_complete",
                "message": "Phase 1 parallel processing completed successfully",
                "processing_time": result.processing_time,
                "target_met": result.processing_time < 30,
                "next_phase": "Phase 2 available - transcription → summarization → slides"
            }
        else:
            # Handle Phase 1 failure
            update_video_job(
                job_id,
                status="failed",
                error=result.error,
                progress={"phase": "phase1_failed", "error": result.error}
            )
            
            jlog(log, logging.ERROR,
                 event="phase1_failed",
                 job_id=job_id,
                 error=result.error,
                 processing_time=result.processing_time)
            
            raise HTTPException(
                status_code=500,
                detail=f"Phase 1 processing failed: {result.error}"
            )
            
    except Exception as e:
        # Handle orchestration errors
        error_msg = f"Video processing failed: {str(e)}"
        
        update_video_job(
            job_id,
            status="failed", 
            error=error_msg,
            progress={"phase": "orchestration_failed", "error": error_msg}
        )
        
        jlog(log, logging.ERROR,
             event="video_processing_exception",
             job_id=job_id,
             error=error_msg)
        
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/video/process-phase2/{job_id}")
async def video_process_phase2(job_id: str):
    """Execute Phase 2: transcription → summarization → slide generation"""
    if job_id not in video_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = video_jobs[job_id]
    
    if job["status"] != "phase1_complete":
        raise HTTPException(
            status_code=400, 
            detail=f"Job must be in phase1_complete status, currently: {job['status']}"
        )
    
    # Update job status
    update_video_job(job_id, status="processing", progress={"phase": "phase2_starting"})
    
    jlog(log, logging.INFO, event="phase2_processing_started", job_id=job_id)
    
    try:
        # Import and initialize Phase 2 orchestrator
        from src.mcp.tools.video_phase2 import Phase2Orchestrator
        
        orchestrator = Phase2Orchestrator(job_id)
        
        # Execute Phase 2 sequential processing
        jlog(log, logging.INFO, event="phase2_starting", job_id=job_id)
        update_video_job(job_id, progress={"phase": "phase2", "status": "processing"})
        
        result = await orchestrator.process_content_pipeline()
        
        if result.success:
            # Update job with Phase 2 results
            update_video_job(
                job_id,
                status="phase2_complete",
                progress={
                    "phase": "phase2_complete",
                    "processing_time": result.processing_time,
                    "transcription_success": result.transcription.success if result.transcription else False,
                    "content_success": result.content.success if result.content else False,
                    "slides_success": result.slides.success if result.slides else False,
                    "slides_generated": result.slides.slides_generated if result.slides else 0
                },
                phases={
                    **job.get("phases", {}),
                    "phase2": result.processing_time
                }
            )
            
            jlog(log, logging.INFO, 
                 event="phase2_success",
                 job_id=job_id,
                 processing_time=result.processing_time,
                 target_met=result.processing_time < 60,
                 slides_generated=result.slides.slides_generated if result.slides else 0)
            
            return {
                "job_id": job_id,
                "status": "phase2_complete",
                "message": "Phase 2 content processing completed successfully",
                "processing_time": result.processing_time,
                "target_met": result.processing_time < 60,
                "slides_generated": result.slides.slides_generated if result.slides else 0,
                "next_phase": "Phase 3 (composition) - Module 5 implementation pending"
            }
        else:
            # Handle Phase 2 failure
            update_video_job(
                job_id,
                status="failed",
                error=result.error,
                progress={"phase": "phase2_failed", "error": result.error}
            )
            
            jlog(log, logging.ERROR,
                 event="phase2_failure",
                 job_id=job_id,
                 error=result.error)
            
            return {
                "job_id": job_id,
                "status": "failed",
                "error": result.error
            }
    
    except Exception as e:
        error_msg = f"Phase 2 processing failed: {str(e)}"
        
        # Update job with error
        update_video_job(
            job_id,
            status="failed",
            error=error_msg,
            progress={"phase": "phase2_failed", "error": error_msg}
        )
        
        jlog(log, logging.ERROR,
             event="phase2_processing_exception",
             job_id=job_id,
             error=error_msg)
        
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/video/preview/{job_id}")
async def video_preview(job_id: str):
    """Generate preview data for Module 4 UI"""
    if job_id not in video_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = video_jobs[job_id]
    
    if job["status"] != "phase2_complete":
        raise HTTPException(
            status_code=400, 
            detail=f"Job must be in phase2_complete status, currently: {job['status']}"
        )
    
    try:
        # Get summary from Phase 2 orchestrator
        from src.mcp.tools.video_phase2 import Phase2Orchestrator
        orchestrator = Phase2Orchestrator(job_id)
        status = await orchestrator.get_processing_status()
        
        # Construct slide URLs
        slides_dir = Path(f"/tmp/jobs/{job_id}/slides")
        slide_files = list(slides_dir.glob("*.png")) if slides_dir.exists() else []
        slide_urls = [f"/tmp/jobs/{job_id}/slides/{f.name}" for f in sorted(slide_files)]
        
        # Mock summary data for demo (in production, this would come from saved state)
        mock_summary = {
            "bullet_points": [
                {"timestamp": "00:30", "text": "Our goal is to demonstrate AI transformation", "confidence": 0.9, "duration": 20.0},
                {"timestamp": "01:15", "text": "Data shows significant improvements", "confidence": 0.8, "duration": 25.0},
                {"timestamp": "02:00", "text": "Recommendation: implement company-wide", "confidence": 0.9, "duration": 15.0}
            ],
            "main_themes": ["Strategy", "Data", "Implementation"],
            "total_duration": "02:30",
            "language": "en",
            "summary_confidence": 0.85
        }
        
        # Mock video metadata
        video_metadata = {
            "width": 1280,
            "height": 720,
            "duration": 150.0,
            "fps": 30
        }
        
        # Mock crop region from face detection
        crop_region = {
            "x": 483,
            "y": 256, 
            "width": 379,
            "height": 379
        }
        
        # Processing stats
        processing_stats = {
            "phase1_time": job.get("phases", {}).get("phase1", 4.56),
            "phase2_time": job.get("phases", {}).get("phase2", 3.39),
            "slides_generated": len(slide_urls)
        }
        
        return {
            "job_id": job_id,
            "summary": mock_summary,
            "slide_urls": slide_urls,
            "video_metadata": video_metadata,
            "crop_region": crop_region,
            "processing_stats": processing_stats
        }
        
    except Exception as e:
        error_msg = f"Failed to generate preview: {str(e)}"
        jlog(log, logging.ERROR,
             event="video_preview_exception",
             job_id=job_id,
             error=error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@app.put("/video/bullets/{job_id}")
async def update_bullets(job_id: str, summary: dict):
    """Update bullet points and regenerate slides"""
    if job_id not in video_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = video_jobs[job_id]
    
    # Validate minimum bullet points
    bullet_points = summary.get("bullet_points", [])
    if len(bullet_points) < 3:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum 3 bullet points required. Current: {len(bullet_points)}"
        )
    
    try:
        jlog(log, logging.INFO,
             event="bullets_update_start",
             job_id=job_id,
             bullet_count=len(bullet_points))
        
        # TODO: Integrate with PlaywrightAgent to regenerate slides
        # For now, simulate the update
        await asyncio.sleep(2)  # Simulate processing time
        
        # Update job with new summary
        update_video_job(job_id, summary=summary)
        
        # Mock response with updated slide URLs
        slides_dir = Path(f"/tmp/jobs/{job_id}/slides")
        slide_files = list(slides_dir.glob("*.png")) if slides_dir.exists() else []
        slide_urls = [f"/tmp/jobs/{job_id}/slides/{f.name}" for f in sorted(slide_files)]
        
        response = {
            "job_id": job_id,
            "summary": summary,
            "slide_urls": slide_urls,
            "video_metadata": {"width": 1280, "height": 720, "duration": 150.0, "fps": 30},
            "crop_region": {"x": 483, "y": 256, "width": 379, "height": 379},
            "processing_stats": {
                "phase1_time": 4.56,
                "phase2_time": 3.39,
                "slides_generated": len(slide_urls)
            }
        }
        
        jlog(log, logging.INFO,
             event="bullets_update_success",
             job_id=job_id,
             slides_regenerated=len(slide_urls))
        
        return response
        
    except Exception as e:
        error_msg = f"Failed to update bullet points: {str(e)}"
        jlog(log, logging.ERROR,
             event="bullets_update_exception",
             job_id=job_id,
             error=error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@app.put("/video/crop/{job_id}")
async def update_crop(job_id: str, crop_region: dict):
    """Update face crop region for final composition"""
    if job_id not in video_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    try:
        # Validate crop region
        required_fields = ["x", "y", "width", "height"]
        for field in required_fields:
            if field not in crop_region:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
            if not isinstance(crop_region[field], (int, float)) or crop_region[field] < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid {field} value: must be non-negative number"
                )
        
        # Update job with new crop region
        update_video_job(job_id, crop_region=crop_region)
        
        jlog(log, logging.INFO,
             event="crop_region_updated",
             job_id=job_id,
             crop_region=crop_region)
        
        return {"success": True, "crop_region": crop_region}
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to update crop region: {str(e)}"
        jlog(log, logging.ERROR,
             event="crop_update_exception",
             job_id=job_id,
             error=error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/video/generate/{job_id}")
async def generate_final_video(job_id: str):
    """Start Phase 3: Final video composition with 50/50 layout and timed slides"""
    if job_id not in video_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = video_jobs[job_id]
    
    if job["status"] not in ["phase2_complete", "editing_complete"]:
        raise HTTPException(
            status_code=400,
            detail=f"Job must be in phase2_complete or editing_complete status, currently: {job['status']}"
        )
    
    try:
        # Update job status to phase3_processing
        update_video_job(job_id, status="phase3_processing")
        
        jlog(log, logging.INFO,
             event="phase3_composition_start",
             job_id=job_id)
        
        # Start Phase 3 composition in background
        from src.mcp.tools.video_phase3 import Phase3Orchestrator
        orchestrator = Phase3Orchestrator(job_id)
        
        # Create background task for composition
        background_thread = threading.Thread(
            target=_run_phase3_composition,
            args=(job_id, orchestrator)
        )
        background_thread.daemon = True
        background_thread.start()
        
        return {
            "job_id": job_id,
            "status": "phase3_processing",
            "message": "Final video composition started"
        }
        
    except Exception as e:
        error_msg = f"Failed to start final video generation: {str(e)}"
        update_video_job(job_id, status="failed", error=error_msg)
        jlog(log, logging.ERROR,
             event="phase3_composition_exception",
             job_id=job_id,
             error=error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


def _run_phase3_composition(job_id: str, orchestrator):
    """Background task for Phase 3 video composition"""
    try:
        jlog(log, logging.INFO,
             event="phase3_background_start",
             job_id=job_id)
        
        # Run the composition process
        result = orchestrator.compose_final_video()
        
        if result.get("success"):
            update_video_job(job_id, 
                           status="completed",
                           final_video_path=result.get("output_path"),
                           composition_time=result.get("processing_time"))
            
            jlog(log, logging.INFO,
                 event="phase3_composition_success",
                 job_id=job_id,
                 output_path=result.get("output_path"),
                 processing_time=result.get("processing_time"))
        else:
            error_msg = result.get("error", "Unknown composition error")
            update_video_job(job_id, status="failed", error=error_msg)
            jlog(log, logging.ERROR,
                 event="phase3_composition_failed",
                 job_id=job_id,
                 error=error_msg)
            
    except Exception as e:
        error_msg = f"Phase 3 composition failed: {str(e)}"
        update_video_job(job_id, status="failed", error=error_msg)
        jlog(log, logging.ERROR,
             event="phase3_background_exception",
             job_id=job_id,
             error=error_msg)


@app.get("/video/result/{job_id}")
async def video_result(job_id: str):
    """Get video processing result and download information"""
    if job_id not in video_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = video_jobs[job_id]
    
    if job["status"] in ["processing", "phase1_processing", "phase2_processing", "phase3_processing"]:
        return {"job_id": job_id, "status": job["status"], "message": "Still processing..."}
    elif job["status"] == "failed":
        return {"job_id": job_id, "status": "failed", "error": job.get("error")}
    elif job["status"] == "completed":
        final_video_path = job.get("final_video_path")
        if final_video_path and Path(final_video_path).exists():
            return {
                "job_id": job_id, 
                "status": "completed",
                "download_url": f"/video/download/{job_id}",
                "file_size": Path(final_video_path).stat().st_size,
                "composition_time": job.get("composition_time"),
                "message": "Video ready for download"
            }
        else:
            return {
                "job_id": job_id,
                "status": "completed",
                "message": "Processing complete but file not found"
            }
    else:
        return {"job_id": job_id, "status": job["status"], "message": "Ready for processing"}


@app.get("/video/download/{job_id}")
async def download_video(job_id: str):
    """Download the final composed video file"""
    if job_id not in video_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = video_jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Video not ready for download. Status: {job['status']}"
        )
    
    final_video_path = job.get("final_video_path")
    if not final_video_path or not Path(final_video_path).exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    from fastapi.responses import FileResponse
    
    # Generate a meaningful filename
    filename = f"presgen_video_{job_id}.mp4"
    
    jlog(log, logging.INFO,
         event="video_download_start",
         job_id=job_id,
         file_path=final_video_path,
         filename=filename)
    
    return FileResponse(
        path=final_video_path,
        filename=filename,
        media_type="video/mp4",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


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
