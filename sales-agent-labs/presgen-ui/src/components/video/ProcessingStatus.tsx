'use client'

import { useState, useEffect } from "react"
import { ProgressBar } from "./ProgressBar"
import { getVideoJobStatus } from "@/lib/video-api"
import { VideoJobStatus } from "@/lib/video-schemas"
import { toast } from "sonner"
import { AlertCircle, CheckCircle } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ProcessingStatusProps {
  jobId: string
  onPhase1Complete?: () => void
  onPhase2Complete?: () => void
  onError?: (error: string) => void
  className?: string
}

interface SubTask {
  name: string
  status: 'completed' | 'in_progress' | 'pending'
  duration?: number
  confidence?: number
}

export function ProcessingStatus({
  jobId,
  onPhase1Complete,
  onPhase2Complete,
  onError,
  className
}: ProcessingStatusProps) {
  const [jobStatus, setJobStatus] = useState<VideoJobStatus | null>(null)
  const [isPolling, setIsPolling] = useState(true)
  const [startTime] = useState(Date.now())
  const [currentPhase, setCurrentPhase] = useState<1 | 2 | 3>(1)

  useEffect(() => {
    if (!isPolling) return

    const pollStatus = async () => {
      try {
        const status = await getVideoJobStatus(jobId)
        setJobStatus(status)

        // Handle phase transitions
        if (status.status === "phase1_complete" && currentPhase === 1) {
          setCurrentPhase(2)
          onPhase1Complete?.()
          toast.success("Phase 1 completed! Starting content processing...")
        } else if (status.status === "phase2_complete" && currentPhase === 2) {
          setCurrentPhase(3)
          onPhase2Complete?.()
          toast.success("Phase 2 completed! Ready for preview and editing.")
          setIsPolling(false)
        } else if (status.status === "failed") {
          setIsPolling(false)
          const errorMessage = status.error || "Processing failed"
          onError?.(errorMessage)
          toast.error(errorMessage)
        } else if (status.status === "completed") {
          setIsPolling(false)
          toast.success("Video processing completed successfully!")
        }

      } catch (error) {
        console.error('Error polling job status:', error)
        // Don't stop polling for network errors, just log them
      }
    }

    // Initial poll
    pollStatus()

    // Set up polling interval
    const interval = setInterval(pollStatus, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
  }, [jobId, isPolling, currentPhase, onPhase1Complete, onPhase2Complete, onError])

  if (!jobStatus) {
    return (
      <div className={`p-6 border rounded-lg bg-white ${className}`}>
        <div className="flex items-center gap-3">
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span>Initializing video processing...</span>
        </div>
      </div>
    )
  }

  // Calculate timing
  const timeElapsed = Math.floor((Date.now() - startTime) / 1000)

  // Create sub-tasks based on current phase and status
  const getSubTasks = (): SubTask[] => {
    if (currentPhase === 1) {
      return [
        {
          name: "Audio extraction",
          status: jobStatus.status === "uploaded" ? "pending" : "completed",
          duration: 2.3,
          confidence: undefined
        },
        {
          name: "Face detection",
          status: jobStatus.status === "processing" ? "in_progress" : 
                   jobStatus.status === "phase1_complete" ? "completed" : "pending",
          duration: 3.1,
          confidence: 0.82
        },
        {
          name: "Video metadata analysis",
          status: jobStatus.status === "phase1_complete" ? "completed" : "pending",
          duration: 1.2
        }
      ]
    } else if (currentPhase === 2) {
      return [
        {
          name: "Audio transcription",
          status: currentPhase > 2 ? "completed" : 
                   jobStatus.status === "processing" ? "in_progress" : "pending",
          duration: 1.0
        },
        {
          name: "Content summarization",
          status: currentPhase > 2 ? "completed" : "pending",
          duration: 0.5
        },
        {
          name: "Professional slide generation",
          status: jobStatus.status === "phase2_complete" ? "completed" : "pending",
          duration: 2.9
        }
      ]
    } else {
      return [
        {
          name: "50/50 video composition",
          status: "pending",
          duration: undefined
        },
        {
          name: "Final rendering",
          status: "pending", 
          duration: undefined
        }
      ]
    }
  }

  // Calculate progress percentage within current phase
  const getPhasePercentage = (): number => {
    switch (jobStatus.status) {
      case "uploaded":
        return 10
      case "processing":
        if (currentPhase === 1) return 60
        if (currentPhase === 2) return 70
        return 80
      case "phase1_complete":
        return currentPhase === 1 ? 100 : 30
      case "phase2_complete":
        return currentPhase === 2 ? 100 : 85
      case "completed":
        return 100
      default:
        return 0
    }
  }

  const getCurrentTask = (): string => {
    if (currentPhase === 1 && jobStatus.status === "processing") {
      return "Analyzing video frames for face detection..."
    } else if (currentPhase === 2 && jobStatus.status === "processing") {
      return "Generating professional slides from transcript..."
    } else if (currentPhase === 3) {
      return "Composing final video with timed slide overlays..."
    }
    return ""
  }

  // Estimate remaining time based on targets and current progress
  const getTimeRemaining = (): number => {
    if (currentPhase === 1 && jobStatus.status === "processing") {
      return Math.max(0, 30 - timeElapsed) // Phase 1 target: 30s
    } else if (currentPhase === 2 && jobStatus.status === "processing") {
      return Math.max(0, 60 - timeElapsed) // Phase 2 target: 60s
    }
    return 0
  }

  // Handle error state
  if (jobStatus.status === "failed") {
    return (
      <div className={`p-6 border border-red-200 rounded-lg bg-red-50 ${className}`}>
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-medium text-red-900 mb-1">Processing Failed</h3>
            <p className="text-sm text-red-700 mb-3">
              {jobStatus.error || "An unexpected error occurred during video processing."}
            </p>
            <Button 
              size="sm" 
              variant="outline" 
              onClick={() => {
                setIsPolling(true)
                setCurrentPhase(1)
                toast.info("Retrying video processing...")
              }}
            >
              Retry Processing
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Handle completion state
  if (jobStatus.status === "phase2_complete") {
    return (
      <div className={`p-6 border border-green-200 rounded-lg bg-green-50 ${className}`}>
        <div className="flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-green-500" />
          <div>
            <h3 className="font-medium text-green-900">Processing Complete!</h3>
            <p className="text-sm text-green-700">
              Your video has been processed successfully. You can now preview and edit the content below.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <ProgressBar
      phase={currentPhase}
      percentage={getPhasePercentage()}
      currentTask={getCurrentTask()}
      timeElapsed={timeElapsed}
      timeRemaining={getTimeRemaining()}
      subTasks={getSubTasks()}
      className={className}
    />
  )
}