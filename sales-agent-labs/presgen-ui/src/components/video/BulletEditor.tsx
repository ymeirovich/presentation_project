'use client'

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { BulletPoint, VideoSummary } from "@/lib/video-schemas"
import { updateBulletPoints } from "@/lib/video-api"
import { toast } from "sonner"
import { 
  Edit3, 
  Plus, 
  X, 
  Clock, 
  Eye, 
  EyeOff, 
  AlertCircle, 
  Save, 
  Loader2,
  Info
} from "lucide-react"
import { cn } from "@/lib/utils"

interface BulletEditorProps {
  jobId: string
  initialSummary: VideoSummary
  onSummaryChange?: (summary: VideoSummary) => void
  className?: string
}

interface BulletEditingState extends BulletPoint {
  id: string
  isEditing: boolean
}

export function BulletEditor({ 
  jobId, 
  initialSummary, 
  onSummaryChange, 
  className 
}: BulletEditorProps) {
  const [bullets, setBullets] = useState<BulletEditingState[]>([])
  const [themes, setThemes] = useState<string[]>(initialSummary.main_themes)
  const [showConfidence, setShowConfidence] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  // Initialize bullets from summary
  useEffect(() => {
    const initialBullets = initialSummary.bullet_points.map((bullet, index) => ({
      ...bullet,
      id: `bullet-${index}`,
      isEditing: false
    }))
    setBullets(initialBullets)
  }, [initialSummary])

  // Check for minimum bullet count
  const hasMinimumBullets = bullets.length >= 3
  const missingBulletCount = Math.max(0, 3 - bullets.length)

  const validateTimestamp = (timestamp: string): boolean => {
    const timestampRegex = /^\d{2}:\d{2}$/
    return timestampRegex.test(timestamp)
  }

  const validateOverlap = (bulletId: string, timestamp: string, duration: number): boolean => {
    const startTime = parseTimestamp(timestamp)
    const endTime = startTime + duration
    
    return !bullets.some(bullet => {
      if (bullet.id === bulletId) return false
      
      const bulletStart = parseTimestamp(bullet.timestamp)
      const bulletEnd = bulletStart + bullet.duration
      
      // Check for overlap
      return (startTime < bulletEnd && endTime > bulletStart)
    })
  }

  const parseTimestamp = (timestamp: string): number => {
    const [minutes, seconds] = timestamp.split(':').map(Number)
    return (minutes * 60) + seconds
  }

  const formatTimestamp = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const updateBullet = (id: string, updates: Partial<BulletPoint>) => {
    setBullets(prev => prev.map(bullet => 
      bullet.id === id ? { ...bullet, ...updates } : bullet
    ))
    setHasUnsavedChanges(true)
  }

  const startEditing = (id: string) => {
    setBullets(prev => prev.map(bullet => 
      bullet.id === id ? { ...bullet, isEditing: true } : { ...bullet, isEditing: false }
    ))
  }

  const stopEditing = (id: string) => {
    setBullets(prev => prev.map(bullet => 
      bullet.id === id ? { ...bullet, isEditing: false } : bullet
    ))
  }

  const addBullet = () => {
    const lastBullet = bullets[bullets.length - 1]
    const newStartTime = lastBullet 
      ? parseTimestamp(lastBullet.timestamp) + lastBullet.duration + 5 
      : 0
    
    const newBullet: BulletEditingState = {
      id: `bullet-${Date.now()}`,
      timestamp: formatTimestamp(newStartTime),
      text: "New bullet point",
      confidence: 0.7,
      duration: 30,
      isEditing: true
    }
    
    setBullets(prev => [...prev, newBullet])
    setHasUnsavedChanges(true)
  }

  const removeBullet = (id: string) => {
    if (bullets.length <= 3) {
      toast.error("Cannot remove bullet - minimum 3 required")
      return
    }
    
    setBullets(prev => prev.filter(bullet => bullet.id !== id))
    setHasUnsavedChanges(true)
  }

  const saveChanges = async () => {
    if (!hasMinimumBullets) {
      toast.error("At least 3 bullet points required")
      return
    }

    setIsSaving(true)
    
    try {
      const updatedSummary: VideoSummary = {
        ...initialSummary,
        bullet_points: bullets.map(({ id, isEditing, ...bullet }) => bullet),
        main_themes: themes
      }
      
      const response = await updateBulletPoints(jobId, updatedSummary)
      
      onSummaryChange?.(updatedSummary)
      setHasUnsavedChanges(false)
      toast.success("Bullet points updated and slides regenerated!")
      
    } catch (error) {
      console.error('Error updating bullets:', error)
      toast.error("Failed to update bullet points")
    } finally {
      setIsSaving(false)
    }
  }

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return "text-green-600 bg-green-100"
    if (confidence >= 0.6) return "text-yellow-600 bg-yellow-100"
    return "text-red-600 bg-red-100"
  }

  const getConfidenceLabel = (confidence: number): string => {
    if (confidence >= 0.8) return "High"
    if (confidence >= 0.6) return "Medium"
    return "Low"
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Edit3 className="w-5 h-5 text-blue-600" />
              Edit Bullet Points
            </CardTitle>
            <CardDescription>
              Review and edit the generated bullet points. Minimum 3 required.
            </CardDescription>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Label htmlFor="confidence-toggle" className="text-sm">
                Show confidence
              </Label>
              <Switch
                id="confidence-toggle"
                checked={showConfidence}
                onCheckedChange={setShowConfidence}
                size="sm"
              />
              {showConfidence && <Info className="w-4 h-4 text-gray-400" />}
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Error Message for Insufficient Bullets */}
        {!hasMinimumBullets && (
          <div className="border-l-4 border-red-500 bg-red-50 p-4 rounded-r">
            <div className="flex items-center">
              <AlertCircle className="h-5 w-5 text-red-400" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  Insufficient bullet points
                </h3>
                <p className="mt-1 text-sm text-red-700">
                  At least 3 bullet points required for slide generation. 
                  Current count: <strong>{bullets.length}</strong>. 
                  Please add <strong>{missingBulletCount}</strong> more bullet point
                  {missingBulletCount > 1 ? 's' : ''}.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Confidence Score Info */}
        {showConfidence && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-blue-500 mt-0.5" />
              <div className="text-sm text-blue-800">
                <p className="font-medium">Confidence Scores</p>
                <p>These indicate how confident the AI was when extracting each bullet point from the transcript.</p>
                <div className="mt-2 flex gap-3 text-xs">
                  <span className="text-green-600">High (80%+): Very reliable</span>
                  <span className="text-yellow-600">Medium (60-79%): Good quality</span>
                  <span className="text-red-600">Low (&lt;60%): May need review</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Bullet Points List */}
        <div className="space-y-3">
          {bullets.map((bullet, index) => (
            <Card key={bullet.id} className="bg-gray-50">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-sm font-medium text-blue-600">
                    {index + 1}
                  </div>
                  
                  <div className="flex-1 space-y-3">
                    {/* Header with timestamp and confidence */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-gray-500" />
                        {bullet.isEditing ? (
                          <Input
                            value={bullet.timestamp}
                            onChange={(e) => updateBullet(bullet.id, { timestamp: e.target.value })}
                            placeholder="MM:SS"
                            className="w-20 h-7 text-sm"
                            onBlur={() => {
                              if (!validateTimestamp(bullet.timestamp)) {
                                toast.error("Invalid timestamp format (use MM:SS)")
                              }
                            }}
                          />
                        ) : (
                          <Badge variant="outline">{bullet.timestamp}</Badge>
                        )}
                      </div>
                      
                      {showConfidence && (
                        <Badge className={cn("text-xs", getConfidenceColor(bullet.confidence))}>
                          {getConfidenceLabel(bullet.confidence)} ({Math.round(bullet.confidence * 100)}%)
                        </Badge>
                      )}

                      <div className="ml-auto flex items-center gap-1">
                        {!bullet.isEditing ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => startEditing(bullet.id)}
                          >
                            <Edit3 className="w-4 h-4" />
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => stopEditing(bullet.id)}
                          >
                            <Save className="w-4 h-4" />
                          </Button>
                        )}
                        
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => removeBullet(bullet.id)}
                          disabled={bullets.length <= 3}
                          className="text-red-600 hover:text-red-700 disabled:opacity-50"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>

                    {/* Text editing */}
                    {bullet.isEditing ? (
                      <div className="space-y-2">
                        <Textarea
                          value={bullet.text}
                          onChange={(e) => updateBullet(bullet.id, { text: e.target.value })}
                          placeholder="Enter bullet point text..."
                          className="resize-none"
                          rows={2}
                          maxLength={80}
                        />
                        <div className="text-xs text-gray-500 text-right">
                          {bullet.text.length}/80 characters
                        </div>
                      </div>
                    ) : (
                      <p className="text-gray-900 leading-relaxed">{bullet.text}</p>
                    )}

                    {/* Duration slider (when editing) */}
                    {bullet.isEditing && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Label className="text-sm">Duration: {bullet.duration}s</Label>
                          <span className="text-xs text-gray-500">How long to show this slide</span>
                        </div>
                        <Slider
                          value={[bullet.duration]}
                          onValueChange={(value) => updateBullet(bullet.id, { duration: value[0] })}
                          min={15}
                          max={45}
                          step={5}
                          className="w-full"
                        />
                        <div className="flex justify-between text-xs text-gray-500">
                          <span>15s</span>
                          <span>45s</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Add Bullet Button */}
        <Button
          onClick={addBullet}
          variant="outline"
          className="w-full border-dashed border-2 h-12"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Bullet Point
        </Button>

        {/* Themes Section */}
        <div className="space-y-3 pt-4 border-t">
          <Label className="text-sm font-medium">Main Themes</Label>
          <div className="flex flex-wrap gap-2">
            {themes.map((theme, index) => (
              <Badge key={index} variant="secondary" className="text-sm">
                {theme}
              </Badge>
            ))}
          </div>
        </div>

        {/* Save Changes Button */}
        <div className="flex justify-end pt-4 border-t">
          <Button 
            onClick={saveChanges}
            disabled={!hasUnsavedChanges || !hasMinimumBullets || isSaving}
            className="min-w-[160px]"
          >
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Updating...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Save Changes
              </>
            )}
          </Button>
        </div>

        {hasUnsavedChanges && (
          <p className="text-sm text-amber-600 text-center">
            You have unsaved changes. Save to regenerate slides.
          </p>
        )}
      </CardContent>
    </Card>
  )
}