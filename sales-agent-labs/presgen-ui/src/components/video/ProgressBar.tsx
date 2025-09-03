'use client'

import { Progress } from "@/components/ui/progress"
import { CheckCircle, Clock, Loader2, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"

interface SubTask {
  name: string
  status: 'completed' | 'in_progress' | 'pending'
  duration?: number
  confidence?: number
}

interface ProgressBarProps {
  phase: 1 | 2 | 3
  percentage: number
  currentTask?: string
  timeElapsed?: number
  timeRemaining?: number
  subTasks?: SubTask[]
  className?: string
}

const PHASE_NAMES = {
  1: "Audio/Video Processing",
  2: "Content Generation", 
  3: "Final Composition"
}

const PHASE_DESCRIPTIONS = {
  1: "Extracting audio and detecting faces in your video",
  2: "Transcribing audio and generating professional slides", 
  3: "Composing final video with 50/50 layout and timed slides"
}

function SubTaskItem({ task }: { task: SubTask }) {
  const getStatusIcon = () => {
    switch (task.status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
      case 'in_progress':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0" />
      case 'pending':
        return <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
    }
  }

  const getStatusText = () => {
    if (task.status === 'completed' && task.duration) {
      let result = `(${task.duration}s)`
      if (task.confidence) {
        result += ` - ${Math.round(task.confidence * 100)}% confidence`
      }
      return result
    }
    if (task.status === 'in_progress') {
      return "in progress..."
    }
    return "pending"
  }

  return (
    <div className="flex items-start gap-2 text-sm">
      {getStatusIcon()}
      <div className="flex-1 min-w-0">
        <span className={cn(
          "font-medium",
          task.status === 'completed' ? "text-green-700" : 
          task.status === 'in_progress' ? "text-blue-700" : 
          "text-gray-500"
        )}>
          {task.name}
        </span>
        {getStatusText() && (
          <span className="ml-2 text-gray-500 text-xs">
            {getStatusText()}
          </span>
        )}
      </div>
    </div>
  )
}

export function ProgressBar({
  phase,
  percentage,
  currentTask,
  timeElapsed,
  timeRemaining,
  subTasks,
  className
}: ProgressBarProps) {
  const formatTime = (seconds: number) => {
    if (seconds < 60) {
      return `${seconds}s`
    }
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
  }

  // Calculate overall progress (0-100%) across all 3 phases
  const overallProgress = ((phase - 1) * 33.33) + (percentage * 0.3333)

  return (
    <div className={cn("space-y-4 p-6 border rounded-lg bg-white", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            PresGen-Video Processing
          </h3>
          <p className="text-sm text-gray-600">
            {PHASE_DESCRIPTIONS[phase]}
          </p>
        </div>
        <div className="text-right text-sm text-gray-500">
          <div>{Math.round(overallProgress)}% Complete</div>
          {timeRemaining && (
            <div>Est. {formatTime(timeRemaining)} remaining</div>
          )}
        </div>
      </div>

      {/* Overall Progress Bar */}
      <div className="space-y-2">
        <Progress value={overallProgress} className="h-3" />
        <div className="flex justify-between text-xs text-gray-500">
          <span className={cn("font-medium", phase >= 1 ? "text-blue-600" : "")}>
            Phase 1
          </span>
          <span className={cn("font-medium", phase >= 2 ? "text-blue-600" : "")}>
            Phase 2
          </span>
          <span className={cn("font-medium", phase >= 3 ? "text-blue-600" : "")}>
            Phase 3
          </span>
        </div>
      </div>

      {/* Current Phase Details */}
      <div className="bg-gray-50 rounded-lg p-4 space-y-3">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
            <span className="font-medium text-gray-900">
              Phase {phase}: {PHASE_NAMES[phase]}
            </span>
          </div>
          <div className="text-sm text-gray-500">
            {percentage}%
          </div>
        </div>

        {currentTask && (
          <div className="text-sm text-gray-600">
            <Loader2 className="w-4 h-4 inline animate-spin mr-2" />
            {currentTask}
          </div>
        )}

        {/* Sub-tasks */}
        {subTasks && subTasks.length > 0 && (
          <div className="space-y-2 pt-2 border-t border-gray-200">
            {subTasks.map((task, index) => (
              <SubTaskItem key={index} task={task} />
            ))}
          </div>
        )}

        {/* Timing Information */}
        {(timeElapsed || timeRemaining) && (
          <div className="flex justify-between text-xs text-gray-500 pt-2 border-t border-gray-200">
            {timeElapsed && (
              <span>Processing started {formatTime(timeElapsed)} ago</span>
            )}
            {timeRemaining && (
              <span>Estimated completion: {formatTime(timeRemaining)}</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}