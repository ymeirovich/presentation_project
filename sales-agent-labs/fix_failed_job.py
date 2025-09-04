#!/usr/bin/env python3
"""
Fix the failed video composition job
"""

import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').absolute()))

from src.mcp.tools.video_phase3 import Phase3Orchestrator

def fix_job():
    """Fix the specific failed job"""
    job_id = "db562d7f-28de-499f-b148-e578c75fb332"
    
    print(f"🔧 Fixing failed job: {job_id}")
    
    # Remove the empty output file
    output_file = Path(f"/tmp/jobs/{job_id}/output/final_video_{job_id}.mp4")
    if output_file.exists():
        output_file.unlink()
        print(f"✅ Removed empty output file: {output_file}")
    
    # Create orchestrator and run composition
    orchestrator = Phase3Orchestrator(job_id)
    
    print("🎬 Running Phase 3 composition with fixed ffmpeg command...")
    result = orchestrator.compose_final_video()
    
    if result.get("success"):
        print(f"✅ Composition successful!")
        print(f"   Output: {result.get('output_path')}")
        print(f"   Processing time: {result.get('processing_time'):.2f} seconds")
        print(f"   File size: {Path(result.get('output_path')).stat().st_size} bytes")
    else:
        print(f"❌ Composition failed: {result.get('error')}")
        return False
    
    return True

if __name__ == "__main__":
    success = fix_job()
    if success:
        print("\n🎉 Job fixed successfully! You can now download the video.")
    else:
        print("\n⚠️ Job fix failed. Check the logs for details.")