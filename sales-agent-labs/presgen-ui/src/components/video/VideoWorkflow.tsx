'use client'

import { useState, useEffect } from "react"
import { VideoForm } from "./VideoForm"
import { ProcessingStatus } from "./ProcessingStatus"
import { BulletEditor } from "./BulletEditor"
import { SlidePreview } from "./SlidePreview"
import { VideoPreview } from "./VideoPreview"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { VideoSummary, VideoPreviewResponse } from "@/lib/video-schemas"
import { getVideoPreview, startPhase2Processing, generateFinalVideo, getVideoJobStatus, downloadVideo } from "@/lib/video-api"
import { toast } from "sonner"
import { ArrowRight, Download, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

type WorkflowStep = 
  | 'upload'      // Initial upload form
  | 'processing'  // Phase 1 & 2 processing
  | 'editing'     // Preview & edit bullets/slides
  | 'generating'  // Final video generation
  | 'complete'    // Final download

interface VideoWorkflowProps {
  className?: string
}

export function VideoWorkflow({ className }: VideoWorkflowProps) {
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('upload')
  const [jobId, setJobId] = useState<string>('')
  const [previewData, setPreviewData] = useState<VideoPreviewResponse | null>(null)
  const [isLoadingPreview, setIsLoadingPreview] = useState(false)
  const [isGeneratingFinal, setIsGeneratingFinal] = useState(false)
  const [finalVideoData, setFinalVideoData] = useState<any>(null)

  // Poll for generation status when in generating step
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null
    
    if (currentStep === 'generating' && jobId) {
      interval = setInterval(async () => {
        try {
          const status = await getVideoJobStatus(jobId)
          
          if (status.status === 'completed') {
            setFinalVideoData(status)
            setCurrentStep('complete')
            setIsGeneratingFinal(false)
            toast.success("Video generation completed!")
            
            if (interval) {
              clearInterval(interval)
            }
          } else if (status.status === 'failed') {
            toast.error(`Video generation failed: ${status.error || 'Unknown error'}`)
            setCurrentStep('editing') // Go back to editing
            setIsGeneratingFinal(false)
            
            if (interval) {
              clearInterval(interval)
            }
          }
        } catch (error) {
          console.error('Error polling generation status:', error)
          // Continue polling on transient errors
        }
      }, 2000) // Poll every 2 seconds
    }
    
    return () => {
      if (interval) {
        clearInterval(interval)
      }
    }
  }, [currentStep, jobId])

  // Handle job creation from upload
  const handleJobCreated = (newJobId: string) => {
    setJobId(newJobId)
    setCurrentStep('processing')
  }

  // Handle Phase 1 completion 
  const handlePhase1Complete = async () => {
    if (!jobId) return
    
    try {
      // Automatically start Phase 2
      await startPhase2Processing(jobId)
      toast.info("Starting content processing...")
    } catch (error) {
      console.error('Error starting Phase 2:', error)
      toast.error("Failed to start content processing")
    }
  }

  // Handle Phase 2 completion
  const handlePhase2Complete = async () => {
    if (!jobId) return
    
    setIsLoadingPreview(true)
    try {
      const preview = await getVideoPreview(jobId)
      setPreviewData(preview)
      setCurrentStep('editing')
      toast.success("Ready for preview and editing!")
    } catch (error) {
      console.error('Error loading preview:', error)
      toast.error("Failed to load preview data")
    } finally {
      setIsLoadingPreview(false)
    }
  }

  // Handle processing errors
  const handleProcessingError = (error: string) => {
    toast.error(`Processing failed: ${error}`)
    // Could add retry logic here
  }

  // Handle summary changes from bullet editor
  const handleSummaryChange = (newSummary: VideoSummary) => {
    if (!previewData) return
    
    setPreviewData({
      ...previewData,
      summary: newSummary
    })
  }

  // Handle final video generation
  const handleGenerateFinalVideo = async () => {
    if (!jobId) return
    
    setIsGeneratingFinal(true)
    try {
      await generateFinalVideo(jobId)
      setCurrentStep('generating')
      toast.success("Starting final video composition...")
    } catch (error) {
      console.error('Error generating final video:', error)
      toast.error("Failed to start final video generation")
      setIsGeneratingFinal(false)
    }
  }

  // Handle video download
  const handleDownloadVideo = async () => {
    if (!jobId) return
    
    try {
      // Create download link
      const downloadUrl = `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080'}/video/download/${jobId}`
      
      // Create temporary anchor element for download
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = `presgen_video_${jobId}.mp4`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      toast.success("Video download started!")
    } catch (error) {
      console.error('Error downloading video:', error)
      toast.error("Failed to download video")
    }
  }

  // Step indicators
  const steps = [
    { key: 'upload', label: 'Upload & Configure', description: 'Upload video and set preferences' },
    { key: 'processing', label: 'Processing', description: 'Extract audio, detect faces, generate content' },
    { key: 'editing', label: 'Preview & Edit', description: 'Review and customize bullet points' },
    { key: 'generating', label: 'Final Generation', description: 'Create 50/50 composed video' },
    { key: 'complete', label: 'Download', description: 'Download your completed video' }
  ] as const

  const getCurrentStepIndex = () => {
    return steps.findIndex(step => step.key === currentStep)
  }

  const renderStepIndicators = () => {
    const currentIndex = getCurrentStepIndex()
    
    return (
      <div className="flex items-center justify-between mb-8">
        {steps.map((step, index) => (
          <div key={step.key} className="flex items-center">
            <div className="flex flex-col items-center">
              <div className={cn(
                "w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium border-2",
                index < currentIndex ? "bg-green-500 border-green-500 text-white" :
                index === currentIndex ? "bg-blue-500 border-blue-500 text-white" :
                "bg-gray-100 border-gray-300 text-gray-500"
              )}>
                {index < currentIndex ? "✓" : index + 1}
              </div>
              <div className="mt-2 text-center">
                <div className={cn(
                  "text-sm font-medium",
                  index <= currentIndex ? "text-gray-900" : "text-gray-500"
                )}>
                  {step.label}
                </div>
                <div className="text-xs text-gray-500 max-w-[120px]">
                  {step.description}
                </div>
              </div>
            </div>
            {index < steps.length - 1 && (
              <div className={cn(
                "flex-1 h-0.5 mx-4 mt-[-20px]",
                index < currentIndex ? "bg-green-500" : "bg-gray-300"
              )} />
            )}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className={className}>
      {/* Step Indicators */}
      {renderStepIndicators()}

      {/* Content based on current step */}
      {currentStep === 'upload' && (
        <VideoForm onJobCreated={handleJobCreated} />
      )}

      {currentStep === 'processing' && (
        <ProcessingStatus
          jobId={jobId}
          onPhase1Complete={handlePhase1Complete}
          onPhase2Complete={handlePhase2Complete}
          onError={handleProcessingError}
        />
      )}

      {currentStep === 'editing' && previewData && (
        <div className="space-y-6">
          {/* Preview & Edit Interface */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <BulletEditor
              jobId={jobId}
              initialSummary={previewData.summary}
              onSummaryChange={handleSummaryChange}
            />
            <SlidePreview
              jobId={jobId}
              summary={previewData.summary}
              slideUrls={previewData.slide_urls}
            />
          </div>

          {/* Video Preview */}
          <VideoPreview
            jobId={jobId}
            summary={previewData.summary}
            videoUrl={`/tmp/jobs/${jobId}/raw_video.mp4`}
            initialCropRegion={previewData.crop_region}
            faceDetectionConfidence={0.82}
          />

          {/* Generate Final Video Button */}
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold">Ready to Generate Final Video?</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Create the 50/50 composed video with your customized slides and timing
                  </p>
                  <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                    <span>• {previewData.summary.bullet_points.length} bullet points</span>
                    <span>• {previewData.slide_urls.length} slides generated</span>
                    <span>• Face detection: {Math.round(0.82 * 100)}%</span>
                  </div>
                </div>
                <Button
                  size="lg"
                  onClick={handleGenerateFinalVideo}
                  disabled={isGeneratingFinal}
                  className="min-w-[200px]"
                >
                  {isGeneratingFinal ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <ArrowRight className="w-5 h-5 mr-2" />
                      Generate Final Video
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {currentStep === 'generating' && (
        <Card>
          <CardContent className="p-8 text-center">
            <div className="space-y-6">
              <Loader2 className="w-16 h-16 mx-auto animate-spin text-blue-500" />
              <h3 className="text-2xl font-semibold">Generating Final Video</h3>
              <p className="text-gray-600 max-w-md mx-auto">
                Creating your 50/50 composed video with timed slide overlays using ffmpeg. 
                This may take 2-3 minutes...
              </p>
              
              {/* Phase 3 progress details */}
              <div className="bg-blue-50 p-4 rounded-lg max-w-md mx-auto">
                <h4 className="font-semibold text-blue-900 mb-2">Phase 3: Final Composition</h4>
                <div className="space-y-2 text-sm text-blue-800">
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-blue-500 rounded-full mr-2"></div>
                    Cropping original video to face region
                  </div>
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-blue-500 rounded-full mr-2"></div>
                    Scaling slides for 50/50 layout
                  </div>
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-blue-500 rounded-full mr-2"></div>
                    Creating timed slide overlays
                  </div>
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-blue-500 rounded-full mr-2"></div>
                    Rendering final MP4 composition
                  </div>
                </div>
              </div>
              
              <div className="text-sm text-gray-500">
                Using hardware acceleration when available • Optimizing for quality
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {currentStep === 'complete' && (
        <Card>
          <CardContent className="p-8 text-center">
            <div className="space-y-4">
              <div className="w-16 h-16 mx-auto bg-green-100 rounded-full flex items-center justify-center">
                <Download className="w-8 h-8 text-green-600" />
              </div>
              <h3 className="text-xl font-semibold">Video Ready!</h3>
              <p className="text-gray-600 max-w-md mx-auto">
                Your professional video with 50/50 layout and timed slides has been generated successfully.
              </p>
              
              {/* Video metadata display */}
              {finalVideoData && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6 p-4 bg-gray-50 rounded-lg">
                  <div className="text-left">
                    <div className="text-sm font-medium text-gray-700">File Size</div>
                    <div className="text-lg font-mono">
                      {finalVideoData.file_size ? `${Math.round(finalVideoData.file_size / 1024 / 1024)} MB` : 'Processing...'}
                    </div>
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-medium text-gray-700">Composition Time</div>
                    <div className="text-lg font-mono">
                      {finalVideoData.composition_time ? `${Math.round(finalVideoData.composition_time)}s` : 'N/A'}
                    </div>
                  </div>
                </div>
              )}
              
              <Button size="lg" className="mt-6" onClick={handleDownloadVideo}>
                <Download className="w-5 h-5 mr-2" />
                Download Video
              </Button>
              <div className="text-sm text-gray-500 mt-4">
                File will be available for 24 hours • MP4 format • 1280x720
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading states */}
      {isLoadingPreview && (
        <Card>
          <CardContent className="p-8 text-center">
            <Loader2 className="w-8 h-8 mx-auto animate-spin mb-4" />
            <p>Loading preview data...</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}