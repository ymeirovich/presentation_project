from __future__ import annotations
import json, logging, time, uuid, os
from typing import Any

# GCP debug logging setup - controlled by environment variable
_GCP_DEBUG_SETUP = False

def _setup_gcp_debug_logging():
    """Setup GCP client-level debug logging if enabled"""
    global _GCP_DEBUG_SETUP
    if _GCP_DEBUG_SETUP:
        return
    
    enable_gcp_debug = os.getenv("ENABLE_GCP_DEBUG_LOGGING", "false").lower() == "true"
    enable_cloud_logging = os.getenv("ENABLE_CLOUD_LOGGING", "false").lower() == "true"
    
    if enable_gcp_debug:
        # Enable detailed GCP client logging
        logging.getLogger('google.api_core').setLevel(logging.DEBUG)
        logging.getLogger('google.auth').setLevel(logging.DEBUG)
        logging.getLogger('google.cloud').setLevel(logging.DEBUG)
        logging.getLogger('googleapiclient').setLevel(logging.DEBUG)
        logging.getLogger('google_auth_httplib2').setLevel(logging.DEBUG)
        logging.getLogger('urllib3').setLevel(logging.DEBUG)
        
        print(f"🔍 GCP Debug Logging: ENABLED (local only)")
    
    if enable_cloud_logging:
        try:
            import google.cloud.logging
            from google.cloud.logging_v2.handlers import CloudLoggingHandler
            
            client = google.cloud.logging.Client()
            handler = CloudLoggingHandler(client)
            
            # Add to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(handler)
            
            print(f"☁️  GCP Cloud Logging: ENABLED (sending to GCP)")
        except ImportError:
            print("⚠️  GCP Cloud Logging requested but google-cloud-logging not installed")
        except Exception as e:
            print(f"⚠️  GCP Cloud Logging setup failed: {e}")
    else:
        print(f"💰 GCP Cloud Logging: DISABLED (cost optimization)")
    
    _GCP_DEBUG_SETUP = True


def jlog(logger: logging.Logger, level: int, **kv: Any) -> None:
    # Setup GCP logging on first call
    _setup_gcp_debug_logging()
    
    kv.setdefault("ts_ms", int(time.time() * 1000))
    kv.setdefault("level", logging.getLevelName(level))
    if "req_id" not in kv:
        kv["req_id"] = str(uuid.uuid4())  # caller can override; useful for tracing
    
    # Add GCP correlation ID for debugging
    if os.getenv("ENABLE_GCP_DEBUG_LOGGING") == "true":
        kv.setdefault("gcp_trace_id", str(uuid.uuid4())[:8])
    
    logger.log(level, json.dumps(kv, ensure_ascii=False))
