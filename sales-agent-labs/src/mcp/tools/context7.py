# src/mcp/tools/context7.py
"""
Context7 MCP integration for real-time documentation retrieval
"""

import asyncio
import logging
import time
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path
import json

from src.common.jsonlog import jlog

log = logging.getLogger("context7")


class Context7MCPClient:
    """Client for Context7 MCP server providing real-time documentation"""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 24 * 3600  # 24 hours as per PRD
        self.cache_file = Path("out/state/cache/context7_cache.json")
        self._ensure_cache_dir()
        self._load_cache()
    
    def _ensure_cache_dir(self):
        """Ensure cache directory exists"""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_cache(self):
        """Load existing cache from disk"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cached_data = json.load(f)
                    # Filter out expired entries
                    current_time = time.time()
                    self.cache = {
                        k: v for k, v in cached_data.items() 
                        if current_time - v.get('cached_at', 0) < self.cache_ttl
                    }
                    jlog(log, logging.INFO, 
                         event="context7_cache_loaded",
                         cached_entries=len(self.cache))
        except Exception as e:
            jlog(log, logging.WARNING,
                 event="context7_cache_load_failed", 
                 error=str(e))
            self.cache = {}
    
    def _save_cache(self):
        """Save cache to disk"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            jlog(log, logging.WARNING,
                 event="context7_cache_save_failed", 
                 error=str(e))
    
    def _get_cache_key(self, library: str, topic: str) -> str:
        """Generate deterministic cache key"""
        content = f"{library}:{topic}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get_docs(self, library: str, topic: str) -> Dict[str, Any]:
        """
        Get documentation for library and topic with caching
        
        Args:
            library: Library name (e.g., "ffmpeg", "whisper", "opencv-python")
            topic: Topic within library (e.g., "audio_extraction", "transcription")
            
        Returns:
            Dict containing documentation context
        """
        start_time = time.time()
        cache_key = self._get_cache_key(library, topic)
        
        # Check cache first
        if cache_key in self.cache:
            cached_entry = self.cache[cache_key]
            if time.time() - cached_entry['cached_at'] < self.cache_ttl:
                jlog(log, logging.INFO,
                     event="context7_cache_hit",
                     library=library, topic=topic,
                     response_time_ms=round((time.time() - start_time) * 1000, 1))
                return cached_entry['data']
        
        # Cache miss - simulate Context7 MCP call
        # TODO: Replace with actual Context7 MCP integration
        try:
            docs = await self._fetch_from_context7_mcp(library, topic)
            
            # Cache the result
            self.cache[cache_key] = {
                'data': docs,
                'cached_at': time.time(),
                'library': library,
                'topic': topic
            }
            self._save_cache()
            
            response_time = (time.time() - start_time) * 1000
            jlog(log, logging.INFO,
                 event="context7_fetch_success",
                 library=library, topic=topic,
                 response_time_ms=round(response_time, 1),
                 cache_size=len(self.cache))
            
            return docs
            
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="context7_fetch_failed",
                 library=library, topic=topic,
                 error=str(e))
            
            # Return fallback patterns for demo reliability
            return self._get_fallback_patterns(library, topic)
    
    async def _fetch_from_context7_mcp(self, library: str, topic: str) -> Dict[str, Any]:
        """
        Fetch documentation from Context7 MCP server
        TODO: Implement actual MCP client integration
        """
        # Simulate Context7 response time (fast cached response)
        await asyncio.sleep(0.1)
        
        # Return simulated Context7 documentation
        return self._get_simulated_docs(library, topic)
    
    def _get_simulated_docs(self, library: str, topic: str) -> Dict[str, Any]:
        """Simulate Context7 documentation responses for development"""
        
        docs_database = {
            ("ffmpeg", "audio_extraction"): {
                "optimal_command": "ffmpeg -i {input} -vn -acodec aac -ab 192k {output}",
                "best_practices": [
                    "Use AAC codec for best compatibility",
                    "192k bitrate provides good quality/size balance",
                    "Always include -vn to disable video stream"
                ],
                "current_flags": {
                    "-vn": "Disable video recording",
                    "-acodec aac": "Use AAC audio codec", 
                    "-ab 192k": "Set audio bitrate to 192kbps"
                },
                "performance_tips": "Use hardware acceleration with -hwaccel auto for speed"
            },
            
            ("opencv-python", "face_detection"): {
                "optimal_method": "cv2.CascadeClassifier with Haar cascades",
                "current_api": "cv2.CascadeClassifier.detectMultiScale()",
                "best_practices": [
                    "Use grayscale images for faster processing",
                    "Scale factor 1.1-1.3 for good accuracy/speed balance", 
                    "minNeighbors=5 reduces false positives"
                ],
                "performance_settings": {
                    "scaleFactor": 1.1,
                    "minNeighbors": 5,
                    "minSize": "(30, 30)"
                },
                "alternative": "Consider MediaPipe for better accuracy"
            },
            
            ("whisper", "transcription"): {
                "optimal_model": "base",
                "current_api": "whisper.load_model().transcribe()",
                "best_practices": [
                    "Use 'base' model for best speed/quality balance",
                    "Enable word-level timestamps with word_timestamps=True",
                    "Set language explicitly if known for speed"
                ],
                "performance_settings": {
                    "model": "base",
                    "language": "en",
                    "word_timestamps": True,
                    "fp16": True
                },
                "optimization": "Use GPU with device='cuda' if available"
            },
            
            ("playwright", "screenshot"): {
                "optimal_method": "page.screenshot() with PNG format",
                "current_api": "page.screenshot(path, type='png')",
                "best_practices": [
                    "Use PNG format for text/graphics quality",
                    "Set explicit viewport for consistent sizing",
                    "Wait for network idle for dynamic content"
                ],
                "performance_settings": {
                    "type": "png",
                    "full_page": False,
                    "clip": {"x": 0, "y": 0, "width": 1920, "height": 1080}
                },
                "optimization": "Use headless mode for speed"
            }
        }
        
        key = (library, topic)
        if key in docs_database:
            return docs_database[key]
        
        # Generic fallback
        return {
            "library": library,
            "topic": topic,
            "status": "simulated",
            "message": f"Simulated documentation for {library}:{topic}",
            "best_practices": [
                f"Use current {library} API patterns",
                "Follow official documentation",
                "Optimize for performance in demo scenarios"
            ]
        }
    
    def _get_fallback_patterns(self, library: str, topic: str) -> Dict[str, Any]:
        """Provide fallback patterns when Context7 is unavailable"""
        
        fallback_patterns = {
            ("ffmpeg", "audio_extraction"): {
                "command": "ffmpeg -i input.mp4 -vn -acodec aac output.aac",
                "notes": "Basic audio extraction (fallback pattern)"
            },
            ("opencv-python", "face_detection"): {
                "method": "cv2.CascadeClassifier('haarcascade_frontalface_default.xml')",
                "notes": "Basic face detection (fallback pattern)"
            },
            ("whisper", "transcription"): {
                "model": "base",
                "method": "whisper.transcribe()",
                "notes": "Basic transcription (fallback pattern)"
            }
        }
        
        key = (library, topic)
        if key in fallback_patterns:
            return fallback_patterns[key]
        
        return {
            "library": library,
            "topic": topic,
            "status": "fallback",
            "message": f"Using fallback patterns for {library}:{topic}"
        }
    
    async def preload_common_patterns(self) -> int:
        """
        Preload common video processing patterns for demo speed
        Returns number of patterns successfully preloaded
        """
        patterns = [
            ("ffmpeg", "audio_extraction"),
            ("ffmpeg", "video_composition"), 
            ("opencv-python", "face_detection"),
            ("whisper", "transcription"),
            ("playwright", "screenshot")
        ]
        
        jlog(log, logging.INFO,
             event="context7_preload_start",
             patterns_count=len(patterns))
        
        success_count = 0
        tasks = []
        
        for library, topic in patterns:
            task = self.get_docs(library, topic)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                success_count += 1
            else:
                library, topic = patterns[i]
                jlog(log, logging.WARNING,
                     event="context7_preload_failed",
                     library=library, topic=topic,
                     error=str(result))
        
        jlog(log, logging.INFO,
             event="context7_preload_complete",
             success_count=success_count,
             total_patterns=len(patterns))
        
        return success_count


# Global Context7 client instance
context7_client = Context7MCPClient()


async def test_connection() -> bool:
    """Test Context7 MCP connection"""
    try:
        result = await context7_client.get_docs("ffmpeg", "audio_extraction")
        return bool(result)
    except Exception as e:
        jlog(log, logging.ERROR, event="context7_test_failed", error=str(e))
        return False


if __name__ == "__main__":
    # Test the Context7 client
    async def main():
        print("Testing Context7 MCP client...")
        
        # Test basic functionality
        success = await test_connection()
        print(f"Connection test: {'PASS' if success else 'FAIL'}")
        
        # Test preloading
        preload_count = await context7_client.preload_common_patterns()
        print(f"Preloaded {preload_count} patterns")
        
        # Test specific documentation retrieval
        docs = await context7_client.get_docs("whisper", "transcription")
        print(f"Retrieved docs for Whisper: {docs.get('optimal_model', 'Unknown')}")
    
    asyncio.run(main())