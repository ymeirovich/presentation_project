#!/usr/bin/env python3
"""
Test simplified ffmpeg command for full-screen video with SRT subtitle overlay
"""

import subprocess
from pathlib import Path

def test_ffmpeg_composition():
    """Test the simplified ffmpeg command"""
    
    job_id = "db562d7f-28de-499f-b148-e578c75fb332"
    job_dir = Path(f"/tmp/jobs/{job_id}")
    
    # Check if files exist
    raw_video = job_dir / "raw_video.mp4"
    slides_dir = job_dir / "slides"
    
    if not raw_video.exists():
        print(f"❌ Raw video not found: {raw_video}")
        return False
    
    slide_files = list(slides_dir.glob("*.png"))
    if len(slide_files) < 1:
        print(f"❌ No slide files found in: {slides_dir}")
        return False
    
    print(f"✅ Found raw video: {raw_video}")
    print(f"✅ Found {len(slide_files)} slide files")
    
    # Use the first slide
    first_slide = sorted(slide_files)[0]
    output_path = job_dir / "test_output.mp4"
    
    # Mock crop region (from the logs we know these values work)
    crop_region = {"x": 483, "y": 256, "width": 379, "height": 379}
    x, y, w, h = crop_region["x"], crop_region["y"], crop_region["width"], crop_region["height"]
    
    # Build simple ffmpeg command
    cmd = [
        "ffmpeg", "-y",  # Overwrite output
        "-i", str(raw_video),
        "-i", str(first_slide),
        "-filter_complex", f"[0:v]crop={w}:{h}:{x}:{y},scale=640:720[left];[1:v]scale=640:720[right];[left][right]hstack=inputs=2[v]",
        "-map", "[v]",
        "-map", "0:a",
        "-c:v", "libx264",
        "-c:a", "aac", 
        "-preset", "ultrafast",  # Use fastest preset for testing
        "-crf", "23",
        "-r", "30",
        "-t", "10",  # Limit to 10 seconds for testing
        str(output_path)
    ]
    
    print(f"🔧 Testing ffmpeg command...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 1 minute timeout for test
        )
        
        if result.returncode != 0:
            print(f"❌ FFmpeg failed with return code: {result.returncode}")
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")
            return False
        
        if not output_path.exists() or output_path.stat().st_size == 0:
            print(f"❌ Output file not created or empty: {output_path}")
            return False
        
        file_size = output_path.stat().st_size
        print(f"✅ FFmpeg completed successfully!")
        print(f"✅ Output file created: {output_path} ({file_size} bytes)")
        
        # Clean up test file
        output_path.unlink()
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ FFmpeg command timed out")
        return False
    except Exception as e:
        print(f"❌ FFmpeg test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_ffmpeg_composition()
    if success:
        print("\n🎉 FFmpeg test passed! The simplified command should work.")
    else:
        print("\n⚠️  FFmpeg test failed. Check the command or file paths.")