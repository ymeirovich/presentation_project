'use client'

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { FileDrop } from "@/components/FileDrop"
import { VideoFormSchema, VideoFormData, VIDEO_LANGUAGES, VIDEO_FILE_TYPES, MAX_VIDEO_SIZE_MB } from "@/lib/video-schemas"
import { uploadVideo, startVideoProcessing } from "@/lib/video-api"
import { toast } from "sonner"
import { Video, Upload, Settings, Crop, Loader2 } from "lucide-react"

interface VideoFormProps {
  onJobCreated?: (jobId: string) => void
  className?: string
}

export function VideoForm({ onJobCreated, className }: VideoFormProps) {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors }
  } = useForm<VideoFormData>({
    resolver: zodResolver(VideoFormSchema),
    defaultValues: {
      language: "en",
      maxBullets: 5,
      cropMode: "auto"
    }
  })

  const cropMode = watch("cropMode")
  const maxBullets = watch("maxBullets")

  const onSubmit = async (data: VideoFormData) => {
    if (!uploadedFile) {
      toast.error("Please select a video file")
      return
    }

    setIsSubmitting(true)
    
    try {
      // Step 1: Upload video file
      toast.info("Uploading video file...")
      const uploadResponse = await uploadVideo(uploadedFile, data)
      
      // Step 2: Start Phase 1 processing
      toast.info("Starting video processing...")
      await startVideoProcessing(uploadResponse.job_id)
      
      toast.success("Video uploaded successfully! Processing started.")
      
      // Notify parent component
      onJobCreated?.(uploadResponse.job_id)
      
    } catch (error) {
      console.error('Video processing error:', error)
      
      if (error instanceof Error) {
        toast.error(`Failed to process video: ${error.message}`)
      } else {
        toast.error("Failed to process video. Please try again.")
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Video className="w-5 h-5 text-blue-600" />
          PresGen-Video - Upload & Configure
        </CardTitle>
        <CardDescription>
          Upload your video (1-3 minutes) and configure processing settings
        </CardDescription>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* File Upload */}
          <div className="space-y-2">
            <Label>Video File</Label>
            <FileDrop
              accept={VIDEO_FILE_TYPES}
              maxSizeMB={MAX_VIDEO_SIZE_MB}
              onFileSelect={setUploadedFile}
              onFileRemove={() => setUploadedFile(null)}
              selectedFile={uploadedFile}
              disabled={isSubmitting}
              placeholder="Drop your MP4 or MOV file here (max 200MB)"
            />
            {errors.language && (
              <p className="text-sm text-red-500">{errors.language.message}</p>
            )}
          </div>

          {/* Configuration Settings */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Language Selection */}
            <div className="space-y-2">
              <Label htmlFor="language">Language</Label>
              <Select 
                value={watch("language")} 
                onValueChange={(value) => setValue("language", value)}
                disabled={isSubmitting}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select language" />
                </SelectTrigger>
                <SelectContent>
                  {VIDEO_LANGUAGES.map((lang) => (
                    <SelectItem key={lang.value} value={lang.value}>
                      {lang.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.language && (
                <p className="text-sm text-red-500">{errors.language.message}</p>
              )}
            </div>

            {/* Number of Bullet Points */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="maxBullets">Key Points</Label>
                <span className="text-sm text-gray-500">{maxBullets} bullets</span>
              </div>
              <Slider
                value={[maxBullets]}
                onValueChange={(value) => setValue("maxBullets", value[0])}
                min={3}
                max={10}
                step={1}
                disabled={isSubmitting}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>3 min</span>
                <span>10 max</span>
              </div>
              {errors.maxBullets && (
                <p className="text-sm text-red-500">{errors.maxBullets.message}</p>
              )}
            </div>
          </div>

          {/* Cropping Mode */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label htmlFor="cropMode" className="flex items-center gap-2">
                  <Crop className="w-4 h-4" />
                  Face Cropping
                </Label>
                <p className="text-sm text-gray-500">
                  Choose how to crop the speaker's face in the final video
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600">Auto-detect</span>
                <Switch
                  checked={cropMode === "manual"}
                  onCheckedChange={(checked) => setValue("cropMode", checked ? "manual" : "auto")}
                  disabled={isSubmitting}
                />
                <span className="text-sm text-gray-600">Manual</span>
              </div>
            </div>

            {/* Manual Crop Settings */}
            {cropMode === "manual" && (
              <div className="grid grid-cols-2 gap-4 p-4 border rounded-lg bg-gray-50">
                <div className="space-y-2">
                  <Label htmlFor="cropX">X Position</Label>
                  <Input
                    {...register("cropRegion.x", { valueAsNumber: true })}
                    type="number"
                    min={0}
                    disabled={isSubmitting}
                    placeholder="0"
                  />
                  {errors.cropRegion?.x && (
                    <p className="text-sm text-red-500">{errors.cropRegion.x.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="cropY">Y Position</Label>
                  <Input
                    {...register("cropRegion.y", { valueAsNumber: true })}
                    type="number"
                    min={0}
                    disabled={isSubmitting}
                    placeholder="0"
                  />
                  {errors.cropRegion?.y && (
                    <p className="text-sm text-red-500">{errors.cropRegion.y.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="cropWidth">Width</Label>
                  <Input
                    {...register("cropRegion.width", { valueAsNumber: true })}
                    type="number"
                    min={1}
                    disabled={isSubmitting}
                    placeholder="640"
                  />
                  {errors.cropRegion?.width && (
                    <p className="text-sm text-red-500">{errors.cropRegion.width.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="cropHeight">Height</Label>
                  <Input
                    {...register("cropRegion.height", { valueAsNumber: true })}
                    type="number"
                    min={1}
                    disabled={isSubmitting}
                    placeholder="480"
                  />
                  {errors.cropRegion?.height && (
                    <p className="text-sm text-red-500">{errors.cropRegion.height.message}</p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Submit Button */}
          <div className="flex justify-end pt-4">
            <Button 
              type="submit" 
              disabled={!uploadedFile || isSubmitting}
              className="min-w-[200px]"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  Upload & Process Video
                </>
              )}
            </Button>
          </div>

          {/* Processing Info */}
          {isSubmitting && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>Processing started!</strong> This may take 1-2 minutes. 
                You'll see detailed progress updates once processing begins.
              </p>
            </div>
          )}
        </form>
      </CardContent>
    </Card>
  )
}