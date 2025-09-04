# src/mcp/tools/video_slides.py
"""
PlaywrightAgent for professional slide generation with Context7 integration
"""

import asyncio
import logging
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field

from playwright.async_api import async_playwright, Browser, Page
from src.mcp.tools.context7 import context7_client
from src.mcp.tools.video_content import BulletPoint, VideoSummary
from src.common.jsonlog import jlog

log = logging.getLogger("video_slides")


class SlideDesign(BaseModel):
    """Slide design configuration"""
    background_color: str = "#ffffff"
    title_color: str = "#1a365d"
    text_color: str = "#2d3748"
    accent_color: str = "#3182ce"
    font_family: str = "Inter, system-ui, sans-serif"
    slide_width: int = 1280
    slide_height: int = 720


@dataclass
class SlideResult:
    """Individual slide generation result"""
    success: bool
    slide_path: Optional[str]
    timestamp: str
    bullet_text: str
    processing_time: float
    error: Optional[str] = None


@dataclass
class SlidesGenerationResult:
    """Complete slides generation result"""
    success: bool
    slides: List[SlideResult]
    processing_time: float
    slides_generated: int
    design_used: SlideDesign
    error: Optional[str] = None


class PlaywrightAgent:
    """Agent for professional slide generation using Playwright with Context7 optimization"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.job_dir = Path(f"/tmp/jobs/{job_id}")
        self.slides_dir = self.job_dir / "slides"
        self.slides_dir.mkdir(parents=True, exist_ok=True)
        self.browser = None
        self.page = None
        self.design = SlideDesign()
    
    async def generate_slides(self, summary: VideoSummary) -> SlidesGenerationResult:
        """
        Generate professional slide PNGs from video summary
        
        Args:
            summary: VideoSummary with bullet points and themes
            
        Returns:
            SlidesGenerationResult with generated slide files
        """
        start_time = time.time()
        
        jlog(log, logging.INFO,
             event="slides_generation_start",
             job_id=self.job_id,
             bullet_count=len(summary.bullet_points),
             themes=summary.main_themes)
        
        try:
            # Get Context7 patterns for Playwright optimization
            context = await context7_client.get_docs("playwright", "html_to_png")
            
            # Initialize Playwright with Context7 settings
            await self._initialize_playwright(context)
            
            # Generate slides for each bullet point
            slide_results = []
            for i, bullet in enumerate(summary.bullet_points):
                slide_result = await self._generate_single_slide(
                    bullet, i + 1, len(summary.bullet_points), summary.main_themes
                )
                slide_results.append(slide_result)
            
            # Clean up browser
            await self._cleanup_playwright()
            
            processing_time = time.time() - start_time
            
            # Count successful slides
            successful_slides = [s for s in slide_results if s.success]
            
            result = SlidesGenerationResult(
                success=len(successful_slides) > 0,
                slides=slide_results,
                processing_time=processing_time,
                slides_generated=len(successful_slides),
                design_used=self.design
            )
            
            jlog(log, logging.INFO,
                 event="slides_generation_success",
                 job_id=self.job_id,
                 processing_time=round(processing_time, 2),
                 slides_generated=len(successful_slides),
                 total_bullets=len(summary.bullet_points))
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Slides generation failed: {str(e)}"
            
            jlog(log, logging.ERROR,
                 event="slides_generation_exception",
                 job_id=self.job_id,
                 error=error_msg,
                 processing_time=round(processing_time, 2))
            
            # Ensure cleanup even on error
            await self._cleanup_playwright()
            
            return SlidesGenerationResult(
                success=False,
                slides=[],
                processing_time=processing_time,
                slides_generated=0,
                design_used=self.design,
                error=error_msg
            )
    
    async def _initialize_playwright(self, context: Dict[str, Any]):
        """Initialize Playwright with Context7 optimization"""
        
        try:
            # Get Context7 recommended settings
            playwright_settings = context.get("performance_settings", {})
            
            # Update design from Context7 if available
            design_settings = context.get("design_settings", {})
            if design_settings:
                for key, value in design_settings.items():
                    if hasattr(self.design, key):
                        setattr(self.design, key, value)
            
            jlog(log, logging.INFO,
                 event="playwright_initializing",
                 job_id=self.job_id,
                 design_settings=design_settings,
                 context7_guided=bool(design_settings))
            
            # Launch browser with optimized settings
            playwright = await async_playwright().start()
            
            # Use Context7 browser settings or defaults
            browser_options = {
                "headless": playwright_settings.get("headless", True),
                "args": playwright_settings.get("browser_args", ["--no-sandbox"])
            }
            
            self.browser = await playwright.chromium.launch(**browser_options)
            self.page = await self.browser.new_page()
            
            # Set viewport for consistent slide generation
            await self.page.set_viewport_size({
                "width": self.design.slide_width,
                "height": self.design.slide_height
            })
            
            jlog(log, logging.INFO,
                 event="playwright_initialized",
                 job_id=self.job_id,
                 viewport_width=self.design.slide_width,
                 viewport_height=self.design.slide_height)
            
        except Exception as e:
            jlog(log, logging.WARNING,
                 event="playwright_initialization_fallback",
                 job_id=self.job_id,
                 error=str(e))
            
            # Fallback initialization
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            self.page = await self.browser.new_page()
            await self.page.set_viewport_size({
                "width": self.design.slide_width,
                "height": self.design.slide_height
            })
    
    async def _generate_single_slide(self, bullet: BulletPoint, slide_num: int, 
                                   total_slides: int, themes: List[str]) -> SlideResult:
        """Generate a single slide PNG"""
        
        slide_start_time = time.time()
        
        try:
            # Create slide HTML
            html_content = self._create_slide_html(bullet, slide_num, total_slides, themes)
            
            # Set HTML content
            await self.page.set_content(html_content)
            
            # Wait for fonts to load
            await self.page.wait_for_load_state("networkidle")
            
            # Generate filename
            safe_timestamp = bullet.timestamp.replace(":", "-")
            slide_filename = f"slide_{slide_num:02d}_{safe_timestamp}.png"
            slide_path = self.slides_dir / slide_filename
            
            # Take screenshot
            await self.page.screenshot(
                path=str(slide_path),
                full_page=True,
                type="png"
            )
            
            processing_time = time.time() - slide_start_time
            
            jlog(log, logging.INFO,
                 event="slide_generated",
                 job_id=self.job_id,
                 slide_num=slide_num,
                 timestamp=bullet.timestamp,
                 processing_time=round(processing_time, 3),
                 file_size=slide_path.stat().st_size)
            
            return SlideResult(
                success=True,
                slide_path=str(slide_path),
                timestamp=bullet.timestamp,
                bullet_text=bullet.text,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - slide_start_time
            error_msg = f"Slide {slide_num} generation failed: {str(e)}"
            
            jlog(log, logging.ERROR,
                 event="slide_generation_failed",
                 job_id=self.job_id,
                 slide_num=slide_num,
                 error=error_msg,
                 processing_time=round(processing_time, 3))
            
            return SlideResult(
                success=False,
                slide_path=None,
                timestamp=bullet.timestamp,
                bullet_text=bullet.text,
                processing_time=processing_time,
                error=error_msg
            )
    
    def _create_slide_html(self, bullet: BulletPoint, slide_num: int, 
                          total_slides: int, themes: List[str]) -> str:
        """Create HTML content for slide"""
        
        # Choose theme for title (rotate through themes)
        theme_title = themes[slide_num % len(themes)] if themes else "Key Point"
        
        # Create clean, professional slide HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Slide {slide_num}</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    width: {self.design.slide_width}px;
                    height: {self.design.slide_height}px;
                    background: {self.design.background_color};
                    font-family: {self.design.font_family};
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    padding: 80px;
                    position: relative;
                }}
                
                /* Removed slide header styles for clean video output */
                
                /* Removed theme-title styles for clean slide display */
                
                .main-content {{
                    color: {self.design.title_color};
                    font-size: 42px;
                    font-weight: 700;
                    line-height: 1.2;
                    text-align: left;
                    max-width: 100%;
                    word-wrap: break-word;
                }}
                
                /* Removed confidence indicator styles for clean video output */
                
                /* Professional accent line */
                .accent-line {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 6px;
                    background: linear-gradient(90deg, {self.design.accent_color} 0%, {self.design.accent_color}80 100%);
                }}
            </style>
        </head>
        <body>
            <div class="accent-line"></div>
            
            <!-- Removed slide-header with timestamp and counter for clean video output -->
            
            <!-- Removed theme-title for clean slide display -->
            
            <div class="main-content">
                {bullet.text}
            </div>
            
            <!-- Removed confidence indicator for clean video output -->
        </body>
        </html>
        """
        
        return html_content.strip()
    
    async def _cleanup_playwright(self):
        """Clean up Playwright resources"""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
                self.page = None
                
            jlog(log, logging.INFO,
                 event="playwright_cleanup_complete",
                 job_id=self.job_id)
                
        except Exception as e:
            jlog(log, logging.WARNING,
                 event="playwright_cleanup_error",
                 job_id=self.job_id,
                 error=str(e))


if __name__ == "__main__":
    # Test PlaywrightAgent
    async def test_playwright_agent():
        print("Testing PlaywrightAgent...")
        
        # Create mock video summary for testing
        from src.mcp.tools.video_content import BulletPoint, VideoSummary
        
        mock_bullets = [
            BulletPoint(timestamp="00:30", text="Our goal is to increase sales efficiency by 40%", confidence=0.9, duration=20.0),
            BulletPoint(timestamp="01:15", text="Data shows significant improvement in lead conversion", confidence=0.8, duration=25.0),
            BulletPoint(timestamp="02:00", text="Recommendation: implement solution company-wide", confidence=0.9, duration=15.0),
        ]
        
        mock_summary = VideoSummary(
            bullet_points=mock_bullets,
            main_themes=["Sales Strategy", "Data Analysis", "Implementation"],
            total_duration="02:30",
            language="en",
            summary_confidence=0.85
        )
        
        agent = PlaywrightAgent("test_slides_job")
        result = await agent.generate_slides(mock_summary)
        
        print(f"Slides generation: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Processing time: {result.processing_time:.2f} seconds")
        print(f"Slides generated: {result.slides_generated}")
        print(f"Design: {result.design_used.slide_width}x{result.design_used.slide_height}")
        
        if result.slides:
            print(f"\nGenerated slides:")
            for i, slide in enumerate(result.slides):
                if slide.success:
                    print(f"  {i+1}. [{slide.timestamp}] {slide.slide_path} ({slide.processing_time:.2f}s)")
                else:
                    print(f"  {i+1}. [{slide.timestamp}] FAILED: {slide.error}")
        
        if result.error:
            print(f"Error: {result.error}")
    
    asyncio.run(test_playwright_agent())