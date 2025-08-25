from __future__ import annotations
import pathlib
from datetime import datetime
from typing import Any, Dict, Optional
import logging

from tenacity import retry, stop_after_attempt, wait_exponential
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

log = logging.getLogger("agent.imagegen")

# ---- CONFIG ----
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
DEFAULT_LOCATION = "us-central1"  # Imagen is available here
DEFAULT_MODEL = "imagegeneration@006"  # Adjust if your project has a newer one

# If you already have a working token.json from test_vertex.py, this module will reuse it.
TOKEN_PATH = pathlib.Path("token.json")
# If you prefer to keep the client JSON next to your code, put it here:
OAUTH_CLIENT_JSON = pathlib.Path("oauth_client.json")  # optional; see notes below


def _load_credentials() -> Credentials:
    """
    Use the existing token.json if present. If not present and oauth_client.json exists,
    run a local OAuth flow to create token.json. Otherwise, raise a clear error.
    """
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        if creds and creds.valid:
            log.debug("Using cached OAuth token from %s", TOKEN_PATH)
            return creds

    if not OAUTH_CLIENT_JSON.exists():
        raise RuntimeError(
            "No token.json found and oauth_client.json not present.\n"
            "Either copy your working token.json (from test_vertex.py) into the project root, "
            "or save your client config JSON as oauth_client.json to run the OAuth flow once."
        )

    # Run Installed App flow based on your working web/installed client config
    flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_CLIENT_JSON), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    log.info("Saved new OAuth token to %s", TOKEN_PATH)
    return creds


def _vertex_init(project_id: str, location: str, creds: Credentials) -> None:
    vertexai.init(project=project_id, location=location, credentials=creds)


@retry(
    stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.6, min=0.6, max=3)
)
def generate_image(
    *,
    project_id: str,
    prompt: str,
    out_dir: pathlib.Path,
    location: str = DEFAULT_LOCATION,
    model_name: str = DEFAULT_MODEL,
    number_of_images: int = 1,
    aspect_ratio: Optional[str] = None,  # e.g., "16:9", "1:1", "4:3"
    guidance_scale: Optional[int] = None,  # e.g., 50 (higher = adhere more to prompt)
    negative_prompt: Optional[str] = None,
    safety_filter_level: Optional[str] = None,  # e.g., "block_some"
    seed: Optional[int] = None,
) -> list[pathlib.Path]:
    """
    Generate one or more images with Vertex AI Imagen and save to out_dir.
    Returns a list of saved file paths.

    Why parameters:
    - aspect_ratio: consistent layout for Slides (try '16:9' for widescreen).
    - guidance_scale: how strictly to follow the prompt.
    - seed: set for reproducibility across runs.
    """
    creds = _load_credentials()
    _vertex_init(project_id, location, creds)
    model = ImageGenerationModel.from_pretrained(model_name)

    kwargs: Dict[str, Any] = {}
    if aspect_ratio:
        kwargs["aspect_ratio"] = aspect_ratio
    if guidance_scale is not None:
        kwargs["guidance_scale"] = guidance_scale
    if negative_prompt:
        kwargs["negative_prompt"] = negative_prompt
    if safety_filter_level:
        kwargs["safety_filter_level"] = safety_filter_level
    if seed is not None:
        kwargs["seed"] = seed

    log.info("Generating image(s) with Imagen: model=%s, prompt=%r", model_name, prompt)
    images = model.generate_images(
        prompt=prompt,
        number_of_images=number_of_images,
        **kwargs,
    )

    if not images:
        raise RuntimeError("Imagen returned no images.")

    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    saved_paths: list[pathlib.Path] = []

    for idx, img in enumerate(images, start=1):
        fname = f"imagen_{timestamp}_{idx:02d}.png"
        out_path = out_dir / fname

        # SDK images typically have .save(); some versions expose raw bytes
        try:
            img.save(out_path)  # type: ignore[attr-defined]
        except Exception:
            raw = getattr(img, "_image_bytes", None) or getattr(img, "bytes", None)
            if not raw:
                raise RuntimeError("Could not access image bytes to save.")
            out_path.write_bytes(raw)

        saved_paths.append(out_path)
        log.info("Saved image: %s", out_path)

    return saved_paths
