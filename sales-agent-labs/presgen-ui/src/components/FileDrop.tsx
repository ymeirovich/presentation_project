'use client'

import { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Upload, File, X, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { MAX_FILE_SIZE_BYTES } from "@/lib/types"

interface FileDropProps {
  accept?: Record<string, string[]>
  maxSizeMB?: number
  onFileSelect: (file: File) => void
  onFileRemove?: () => void
  selectedFile?: File
  disabled?: boolean
  className?: string
  placeholder?: string
}

export function FileDrop({
  accept,
  maxSizeMB = 10,
  onFileSelect,
  onFileRemove,
  selectedFile,
  disabled = false,
  className,
  placeholder = "Drop files here or click to upload"
}: FileDropProps) {
  const [error, setError] = useState<string>("")

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    setError("")

    if (rejectedFiles.length > 0) {
      const rejection = rejectedFiles[0]
      if (rejection.errors?.[0]?.code === 'file-too-large') {
        setError(`File is too large. Maximum size is ${maxSizeMB}MB.`)
      } else if (rejection.errors?.[0]?.code === 'file-invalid-type') {
        setError("File type not supported.")
      } else {
        setError("File upload failed. Please try again.")
      }
      return
    }

    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0]
      
      // Additional size check
      if (file.size > maxSizeMB * 1024 * 1024) {
        setError(`File is too large. Maximum size is ${maxSizeMB}MB.`)
        return
      }

      onFileSelect(file)
    }
  }, [maxSizeMB, onFileSelect])

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept,
    maxSize: maxSizeMB * 1024 * 1024,
    multiple: false,
    disabled,
    noClick: false,
    noKeyboard: false,
  })

  const removeFile = () => {
    setError("")
    onFileRemove?.()
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getFileIcon = () => <File className="w-4 h-4" />

  if (selectedFile) {
    return (
      <Card className={cn("p-4", className)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getFileIcon()}
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">{selectedFile.name}</p>
              <p className="text-xs text-muted-foreground">
                {formatFileSize(selectedFile.size)}
              </p>
            </div>
          </div>
          
          {onFileRemove && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={removeFile}
              disabled={disabled}
            >
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>

        {error && (
          <div className="mt-3 flex items-center space-x-2 text-sm text-destructive">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </div>
        )}
      </Card>
    )
  }

  return (
    <div className={cn("space-y-2", className)}>
      <Card
        {...getRootProps()}
        className={cn(
          "border-2 border-dashed cursor-pointer transition-colors hover:border-primary/50",
          isDragActive && "border-primary bg-primary/5",
          disabled && "cursor-not-allowed opacity-50",
          error && "border-destructive"
        )}
      >
        <div className="p-8 text-center">
          <input {...getInputProps()} />
          
          <div className="flex flex-col items-center space-y-4">
            <Upload className={cn(
              "w-10 h-10 text-muted-foreground",
              isDragActive && "text-primary"
            )} />
            
            <div className="space-y-2">
              <p className="text-sm font-medium">
                {isDragActive ? "Drop the file here" : placeholder}
              </p>
              
              <p className="text-xs text-muted-foreground">
                Maximum file size: {maxSizeMB}MB
              </p>
            </div>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={open}
              disabled={disabled}
            >
              Choose File
            </Button>
          </div>
        </div>
      </Card>

      {error && (
        <div className="flex items-center space-x-2 text-sm text-destructive">
          <AlertCircle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}