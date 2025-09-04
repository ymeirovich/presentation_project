#!/usr/bin/env python3
"""
Isolated Whisper Subprocess
Run Whisper in a completely separate process to avoid OpenMP conflicts
"""

# Import OpenMP override first
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import openmp_override

import os
import json
import warnings

def setup_openmp_protection():
    """Set all possible OpenMP protection variables"""
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    os.environ['OMP_NUM_THREADS'] = '1'
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['MKL_NUM_THREADS'] = '1'
    os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
    os.environ['NUMEXPR_NUM_THREADS'] = '1'
    os.environ['OMP_MAX_ACTIVE_LEVELS'] = '1'
    
    # Suppress all OpenMP warnings
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", message=".*FP16 is not supported on CPU.*")
    warnings.filterwarnings("ignore", message=".*omp_set_nested.*")

def run_whisper_transcription(audio_path: str, model_name: str = "tiny"):
    """Run Whisper transcription in isolated environment"""
    setup_openmp_protection()
    
    try:
        import whisper
        import torch
        
        # Force single-threaded
        torch.set_num_threads(1)
        
        # Load model
        model = whisper.load_model(model_name, device="cpu")
        
        # Transcribe
        result = model.transcribe(audio_path, fp16=False, verbose=False)
        
        # Extract segments with timing
        segments = []
        for segment in result.get('segments', []):
            segments.append({
                'start_time': segment['start'],
                'end_time': segment['end'],
                'text': segment['text'].strip(),
                'confidence': 1.0,  # Whisper doesn't provide confidence per segment
                'words': []
            })
        
        return {
            'success': True,
            'segments': segments,
            'full_text': result.get('text', ''),
            'language': result.get('language', 'en'),
            'duration': segments[-1]['end_time'] if segments else 0,
            'model_used': model_name,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'segments': [],
            'full_text': '',
            'language': '',
            'duration': 0,
            'model_used': model_name,
            'error': str(e)
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({'success': False, 'error': 'Usage: whisper_subprocess.py <audio_path> [model_name]'}))
        sys.exit(1)
    
    audio_path = sys.argv[1]
    model_name = sys.argv[2] if len(sys.argv) > 2 else "tiny"
    
    if not Path(audio_path).exists():
        print(json.dumps({'success': False, 'error': f'Audio file not found: {audio_path}'}))
        sys.exit(1)
    
    result = run_whisper_transcription(audio_path, model_name)
    print(json.dumps(result, indent=2))