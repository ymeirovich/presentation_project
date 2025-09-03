'use client'

import { useState, useRef, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { VideoSummary, CropRegion } from "@/lib/video-schemas"
import { updateCropRegion } from "@/lib/video-api"
import { toast } from "sonner"
import { 
  Play, 
  Pause, 
  Volume2, 
  VolumeX, 
  Maximize,
  Move,
  Save,
  RotateCcw,
  Loader2,
  Video as VideoIcon
} from "lucide-react"
import { cn } from "@/lib/utils"

interface VideoPreviewProps {
  jobId: string
  summary: VideoSummary
  videoUrl: string
  initialCropRegion?: CropRegion
  faceDetectionConfidence?: number
  onCropChange?: (cropRegion: CropRegion) => void
  className?: string
}

export function VideoPreview({
  jobId,
  summary,
  videoUrl,
  initialCropRegion = { x: 0, y: 0, width: 640, height: 480 },
  faceDetectionConfidence = 0.82,
  onCropChange,
  className
}: VideoPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)
  
  const [cropRegion, setCropRegion] = useState<CropRegion>(initialCropRegion)
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [showCropOverlay, setShowCropOverlay] = useState(true)
  const [isManualCrop, setIsManualCrop] = useState(false)
  const [isSavingCrop, setIsSavingCrop] = useState(false)
  
  // Video event handlers
  const handlePlayPause = () => {
    if (!videoRef.current) return
    
    if (isPlaying) {
      videoRef.current.pause()
    } else {
      videoRef.current.play()
    }
    setIsPlaying(!isPlaying)
  }

  const handleTimeUpdate = () => {
    if (!videoRef.current) return
    setCurrentTime(videoRef.current.currentTime)
  }

  const handleLoadedMetadata = () => {
    if (!videoRef.current) return
    setDuration(videoRef.current.duration)
  }

  const handleSeek = (newTime: number[]) => {
    if (!videoRef.current) return
    videoRef.current.currentTime = newTime[0]
    setCurrentTime(newTime[0])
  }

  const handleVolumeChange = (newVolume: number[]) => {
    if (!videoRef.current) return
    const vol = newVolume[0] / 100
    videoRef.current.volume = vol
    setVolume(vol)
    setIsMuted(vol === 0)
  }

  const toggleMute = () => {
    if (!videoRef.current) return
    const newMuted = !isMuted
    videoRef.current.muted = newMuted
    setIsMuted(newMuted)
  }

  // Crop region handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (!isManualCrop || !containerRef.current) return
    
    const rect = containerRef.current.getBoundingClientRect()
    setIsDragging(true)
    setDragStart({
      x: e.clientX - rect.left - cropRegion.x,
      y: e.clientY - rect.top - cropRegion.y
    })
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !containerRef.current) return
    
    const rect = containerRef.current.getBoundingClientRect()
    const newX = Math.max(0, Math.min(e.clientX - rect.left - dragStart.x, rect.width - cropRegion.width))
    const newY = Math.max(0, Math.min(e.clientY - rect.top - dragStart.y, rect.height - cropRegion.height))
    
    const newCropRegion = { ...cropRegion, x: newX, y: newY }
    setCropRegion(newCropRegion)
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  const resetCropRegion = () => {
    setCropRegion(initialCropRegion)
    toast.info("Crop region reset to face detection")
  }

  const saveCropRegion = async () => {
    setIsSavingCrop(true)
    try {
      await updateCropRegion(jobId, cropRegion)
      onCropChange?.(cropRegion)
      toast.success("Crop region saved successfully")
    } catch (error) {
      console.error('Error saving crop region:', error)
      toast.error("Failed to save crop region")
    } finally {
      setIsSavingCrop(false)
    }
  }

  // Format time helper
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Get bullet point at current time
  const getCurrentBulletPoint = () => {
    return summary.bullet_points.find(bullet => {
      const [minutes, seconds] = bullet.timestamp.split(':').map(Number)
      const bulletTime = minutes * 60 + seconds
      return Math.abs(currentTime - bulletTime) <= bullet.duration / 2
    })
  }

  const currentBullet = getCurrentBulletPoint()

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <VideoIcon className="w-5 h-5 text-blue-600" />
              Video Preview & Crop Adjustment
            </CardTitle>
            <CardDescription>
              Preview your video and adjust the face crop region for final composition
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge className="bg-green-100 text-green-800">
              Face detected: {Math.round(faceDetectionConfidence * 100)}%
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Video Player Container */}
        <div 
          ref={containerRef}
          className="relative bg-black rounded-lg overflow-hidden"
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <video
            ref={videoRef}
            src={videoUrl}
            className="w-full h-auto"
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
          />

          {/* Crop Overlay */}
          {showCropOverlay && (
            <>
              {/* Dark overlay areas */}
              <div className="absolute inset-0 bg-black bg-opacity-50 pointer-events-none" />
              
              {/* Crop window */}
              <div
                className={cn(
                  "absolute border-2 border-blue-400 bg-transparent",
                  isManualCrop && "cursor-move",
                  isDragging && "border-blue-600"
                )}
                style={{
                  left: `${(cropRegion.x / (containerRef.current?.clientWidth || 1)) * 100}%`,
                  top: `${(cropRegion.y / (containerRef.current?.clientHeight || 1)) * 100}%`,
                  width: `${(cropRegion.width / (containerRef.current?.clientWidth || 1)) * 100}%`,
                  height: `${(cropRegion.height / (containerRef.current?.clientHeight || 1)) * 100}%`
                }}
                onMouseDown={handleMouseDown}
              >
                {/* Crop corners for visual feedback */}
                <div className="absolute -top-1 -left-1 w-2 h-2 bg-blue-400 rounded-full" />
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-blue-400 rounded-full" />
                <div className="absolute -bottom-1 -left-1 w-2 h-2 bg-blue-400 rounded-full" />
                <div className="absolute -bottom-1 -right-1 w-2 h-2 bg-blue-400 rounded-full" />
                
                {/* Move icon when hovering */}
                {isManualCrop && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="bg-blue-600 text-white p-2 rounded-full opacity-75">
                      <Move className="w-4 h-4" />
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Video Controls Overlay */}
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
            <div className="flex items-center gap-3">
              <Button
                size="sm"
                variant="ghost"
                onClick={handlePlayPause}
                className="text-white hover:bg-white/20"
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </Button>

              <div className="flex-1">
                <Slider
                  value={[currentTime]}
                  max={duration}
                  step={0.1}
                  onValueChange={handleSeek}
                  className="w-full"
                />
              </div>

              <span className="text-white text-sm font-mono">
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>

              <Button
                size="sm"
                variant="ghost"
                onClick={toggleMute}
                className="text-white hover:bg-white/20"
              >
                {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              </Button>

              <div className="w-24">
                <Slider
                  value={[volume * 100]}
                  max={100}
                  step={1}
                  onValueChange={handleVolumeChange}
                  className="w-full"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Bullet Point Timeline */}
        {summary.bullet_points.length > 0 && (
          <div className="space-y-2">
            <Label className="text-sm font-medium">Bullet Point Timeline</Label>
            <div className="relative h-8 bg-gray-100 rounded">
              {summary.bullet_points.map((bullet, index) => {
                const [minutes, seconds] = bullet.timestamp.split(':').map(Number)
                const bulletTime = minutes * 60 + seconds
                const left = duration > 0 ? (bulletTime / duration) * 100 : 0
                const width = duration > 0 ? (bullet.duration / duration) * 100 : 0
                
                return (
                  <div
                    key={index}
                    className={cn(
                      "absolute top-1 h-6 bg-blue-200 border border-blue-300 rounded text-xs px-1 flex items-center justify-center cursor-pointer",
                      currentBullet?.timestamp === bullet.timestamp && "bg-blue-400 border-blue-500"
                    )}
                    style={{ 
                      left: `${left}%`, 
                      width: `${Math.max(width, 3)}%` 
                    }}
                    onClick={() => handleSeek([bulletTime])}
                    title={`${bullet.timestamp}: ${bullet.text}`}
                  >
                    <span className="truncate">{index + 1}</span>
                  </div>
                )
              })}
            </div>
            {currentBullet && (
              <div className="text-sm text-gray-600">
                <Badge variant="outline" className="mr-2">{currentBullet.timestamp}</Badge>
                {currentBullet.text}
              </div>
            )}
          </div>
        )}

        {/* Crop Controls */}
        <div className="space-y-4 border-t pt-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label className="text-sm font-medium">Crop Region Controls</Label>
              <p className="text-xs text-gray-500">
                Adjust how the speaker's face will appear in the final video
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Label htmlFor="manual-crop" className="text-sm">Manual adjustment</Label>
              <Switch
                id="manual-crop"
                checked={isManualCrop}
                onCheckedChange={setIsManualCrop}
              />
            </div>
          </div>

          {/* Crop Region Info */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <Label className="text-xs text-gray-500">X Position</Label>
              <div className="font-mono">{Math.round(cropRegion.x)}px</div>
            </div>
            <div>
              <Label className="text-xs text-gray-500">Y Position</Label>
              <div className="font-mono">{Math.round(cropRegion.y)}px</div>
            </div>
            <div>
              <Label className="text-xs text-gray-500">Width</Label>
              <div className="font-mono">{Math.round(cropRegion.width)}px</div>
            </div>
            <div>
              <Label className="text-xs text-gray-500">Height</Label>
              <div className="font-mono">{Math.round(cropRegion.height)}px</div>
            </div>
          </div>

          {/* Control Buttons */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Switch
                id="show-overlay"
                checked={showCropOverlay}
                onCheckedChange={setShowCropOverlay}
              />
              <Label htmlFor="show-overlay" className="text-sm">
                Show crop overlay
              </Label>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={resetCropRegion}
                disabled={!isManualCrop}
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Reset
              </Button>
              <Button
                size="sm"
                onClick={saveCropRegion}
                disabled={isSavingCrop || !isManualCrop}
              >
                {isSavingCrop ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    Save Crop
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Instructions */}
          <div className="text-xs text-gray-500 bg-gray-50 rounded p-3">
            <p className="font-medium mb-1">How to adjust crop region:</p>
            <ul className="space-y-1">
              <li>• Enable "Manual adjustment" to modify the crop region</li>
              <li>• Click and drag the blue rectangle to reposition</li>
              <li>• The crop region shows where the speaker will appear in the final 50/50 layout</li>
              <li>• Save your changes to apply them to the final video generation</li>
            </ul>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}