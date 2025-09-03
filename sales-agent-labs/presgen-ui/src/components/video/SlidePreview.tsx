'use client'

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { VideoSummary } from "@/lib/video-schemas"
import { toast } from "sonner"
import { 
  Eye, 
  ZoomIn, 
  ZoomOut, 
  ChevronLeft, 
  ChevronRight,
  Monitor,
  Download,
  Loader2,
  RefreshCw
} from "lucide-react"
import { cn } from "@/lib/utils"
import Image from "next/image"

interface SlidePreviewProps {
  jobId: string
  summary: VideoSummary
  slideUrls: string[]
  onRegenerateSlides?: () => void
  isRegenerating?: boolean
  className?: string
}

export function SlidePreview({
  jobId,
  summary,
  slideUrls,
  onRegenerateSlides,
  isRegenerating = false,
  className
}: SlidePreviewProps) {
  const [selectedSlideIndex, setSelectedSlideIndex] = useState(0)
  const [zoomLevel, setZoomLevel] = useState(100)
  const [imageLoadErrors, setImageLoadErrors] = useState<Set<number>>(new Set())

  // Reset selection when slides change
  useEffect(() => {
    if (selectedSlideIndex >= slideUrls.length) {
      setSelectedSlideIndex(0)
    }
  }, [slideUrls.length, selectedSlideIndex])

  // Keyboard navigation
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        navigateSlide('prev')
      } else if (e.key === 'ArrowRight') {
        e.preventDefault()
        navigateSlide('next')
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [selectedSlideIndex, slideUrls.length])

  const navigateSlide = (direction: 'prev' | 'next') => {
    if (direction === 'prev') {
      setSelectedSlideIndex(prev => prev > 0 ? prev - 1 : slideUrls.length - 1)
    } else {
      setSelectedSlideIndex(prev => prev < slideUrls.length - 1 ? prev + 1 : 0)
    }
  }

  const handleZoom = (newZoom: number) => {
    setZoomLevel(Math.max(50, Math.min(200, newZoom)))
  }

  const handleImageError = (index: number) => {
    setImageLoadErrors(prev => new Set(prev).add(index))
    toast.error(`Failed to load slide ${index + 1}`)
  }

  const getSlideTimestamp = (index: number): string => {
    return summary.bullet_points[index]?.timestamp || "00:00"
  }

  const getSlideTheme = (index: number): string => {
    const themeIndex = index % summary.main_themes.length
    return summary.main_themes[themeIndex] || "Key Point"
  }

  // Create slide preview URL (for demo, we'll construct based on job and slide index)
  const getSlidePreviewUrl = (index: number): string => {
    if (slideUrls[index]) {
      return slideUrls[index]
    }
    // Fallback construction for demo
    return `http://localhost:8080/tmp/jobs/${jobId}/slides/slide_${(index + 1).toString().padStart(2, '0')}.png`
  }

  if (slideUrls.length === 0 || !summary.bullet_points.length) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center h-64 text-gray-500">
          <Monitor className="w-12 h-12 mb-4" />
          <p>No slides available</p>
          <p className="text-sm">Process your video to generate slide previews</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Eye className="w-5 h-5 text-blue-600" />
              Slide Preview
            </CardTitle>
            <CardDescription>
              Preview generated slides with clean, professional formatting
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {onRegenerateSlides && (
              <Button
                size="sm"
                variant="outline"
                onClick={onRegenerateSlides}
                disabled={isRegenerating}
              >
                {isRegenerating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Updating...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Regenerate
                  </>
                )}
              </Button>
            )}
            <Badge variant="secondary">
              {slideUrls.length} slides
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Slide Thumbnails */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {slideUrls.map((_, index) => (
            <div key={index} className="flex-shrink-0">
              <Button
                variant={selectedSlideIndex === index ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedSlideIndex(index)}
                className="h-auto p-2 flex flex-col items-center gap-1"
              >
                <div className="w-16 h-9 bg-gray-100 rounded border flex items-center justify-center text-xs">
                  {imageLoadErrors.has(index) ? (
                    <span className="text-red-500">Error</span>
                  ) : (
                    <Monitor className="w-4 h-4" />
                  )}
                </div>
                <div className="text-xs">
                  <div className="font-medium">{getSlideTimestamp(index)}</div>
                  <div className="text-gray-500">{index + 1}/{slideUrls.length}</div>
                </div>
              </Button>
            </div>
          ))}
        </div>

        {/* Main Preview */}
        <div className="border rounded-lg bg-gray-50">
          {/* Preview Header */}
          <div className="flex items-center justify-between p-3 border-b bg-white rounded-t-lg">
            <div className="flex items-center gap-3">
              <Badge className="bg-blue-100 text-blue-800">
                {getSlideTimestamp(selectedSlideIndex)}
              </Badge>
              <span className="text-sm font-medium text-gray-700">
                {getSlideTheme(selectedSlideIndex)}
              </span>
            </div>
            
            <div className="flex items-center gap-2">
              {/* Navigation */}
              <Button
                size="sm"
                variant="ghost"
                onClick={() => navigateSlide('prev')}
                disabled={slideUrls.length <= 1}
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <span className="text-sm text-gray-500">
                {selectedSlideIndex + 1} / {slideUrls.length}
              </span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => navigateSlide('next')}
                disabled={slideUrls.length <= 1}
              >
                <ChevronRight className="w-4 h-4" />
              </Button>

              {/* Zoom Controls */}
              <div className="border-l pl-2 ml-2 flex items-center gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleZoom(zoomLevel - 25)}
                  disabled={zoomLevel <= 50}
                >
                  <ZoomOut className="w-4 h-4" />
                </Button>
                <span className="text-sm text-gray-500 min-w-[50px] text-center">
                  {zoomLevel}%
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleZoom(zoomLevel + 25)}
                  disabled={zoomLevel >= 200}
                >
                  <ZoomIn className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Preview Content */}
          <div className="p-4 flex justify-center min-h-[400px]">
            {imageLoadErrors.has(selectedSlideIndex) ? (
              <div className="flex flex-col items-center justify-center text-gray-500 h-96">
                <Monitor className="w-16 h-16 mb-4" />
                <p className="text-lg font-medium">Failed to load slide</p>
                <p className="text-sm">Slide {selectedSlideIndex + 1} could not be loaded</p>
                <Button 
                  size="sm" 
                  variant="outline" 
                  className="mt-3"
                  onClick={() => {
                    // Remove from error set to retry
                    setImageLoadErrors(prev => {
                      const newSet = new Set(prev)
                      newSet.delete(selectedSlideIndex)
                      return newSet
                    })
                  }}
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Retry
                </Button>
              </div>
            ) : (
              <div 
                className="transition-transform duration-200 ease-in-out"
                style={{ 
                  transform: `scale(${zoomLevel / 100})`,
                  transformOrigin: 'center top'
                }}
              >
                {/* Slide Preview - Using div with background for demo */}
                <div 
                  className="w-[640px] h-[360px] bg-white rounded-lg shadow-lg border flex flex-col justify-center px-12 relative"
                  style={{
                    backgroundImage: `url(${getSlidePreviewUrl(selectedSlideIndex)})`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    backgroundRepeat: 'no-repeat'
                  }}
                >
                  {/* Fallback content if image doesn't load */}
                  <div className="absolute inset-0 flex flex-col justify-center px-12 bg-gradient-to-br from-blue-50 to-white rounded-lg">
                    {/* Slide Header */}
                    <div className="absolute top-6 right-6 flex items-center gap-3">
                      <Badge className="bg-blue-600 text-white px-3 py-1">
                        {getSlideTimestamp(selectedSlideIndex)}
                      </Badge>
                      <span className="text-sm text-gray-500">
                        {selectedSlideIndex + 1}/{slideUrls.length}
                      </span>
                    </div>

                    {/* Theme */}
                    <div className="text-blue-600 text-lg font-semibold uppercase tracking-wide mb-4">
                      {getSlideTheme(selectedSlideIndex)}
                    </div>

                    {/* Main Content - NO BULLET CIRCLES, clean lines */}
                    <div className="space-y-4">
                      <div className="text-2xl font-bold text-gray-900 leading-tight">
                        {summary.bullet_points[selectedSlideIndex]?.text || "Slide content"}
                      </div>
                    </div>

                    {/* Confidence Indicator */}
                    <div className="absolute bottom-6 left-12 flex items-center gap-2 text-sm text-gray-500">
                      <div className="w-12 h-1 bg-gray-200 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-blue-600 transition-all"
                          style={{ 
                            width: `${(summary.bullet_points[selectedSlideIndex]?.confidence || 0.8) * 100}%` 
                          }}
                        />
                      </div>
                      <span>
                        {Math.round((summary.bullet_points[selectedSlideIndex]?.confidence || 0.8) * 100)}% confidence
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Slide Content Summary */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-2">Current Slide Content</h4>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">
                {getSlideTimestamp(selectedSlideIndex)}
              </Badge>
              <span className="text-gray-600">
                Duration: {summary.bullet_points[selectedSlideIndex]?.duration || 30}s
              </span>
            </div>
            <p className="text-gray-700 leading-relaxed">
              {summary.bullet_points[selectedSlideIndex]?.text || "No content"}
            </p>
          </div>
        </div>

        {/* Keyboard Shortcuts Info */}
        <div className="text-xs text-gray-500 text-center border-t pt-3">
          <p>
            Use <kbd className="px-1 py-0.5 bg-gray-100 rounded text-xs">←</kbd> and <kbd className="px-1 py-0.5 bg-gray-100 rounded text-xs">→</kbd> to navigate slides
          </p>
        </div>
      </CardContent>
    </Card>
  )
}