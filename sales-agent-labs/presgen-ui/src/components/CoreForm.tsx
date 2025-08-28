'use client'

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Slider } from "@/components/ui/slider"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { FileDrop } from "./FileDrop"
import { MarkdownPreview } from "./MarkdownPreview"
import { ServerResponseCard, ServerResponse } from "./ServerResponseCard"
import { CoreFormSchema, CoreFormWithTextSchema, CoreFormData } from "@/lib/schemas"
import { createPresentation, ApiError } from "@/lib/api"
import { ACCEPTED_TEXT_FILES, TEMPLATE_STYLES } from "@/lib/types"
import { toast } from "sonner"
import { FileText, Loader2 } from "lucide-react"

interface CoreFormProps {
  className?: string
}

export function CoreForm({ className }: CoreFormProps) {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [serverResponse, setServerResponse] = useState<ServerResponse | null>(null)

  const form = useForm<CoreFormData>({
    resolver: zodResolver(CoreFormSchema),
    defaultValues: {
      report_text: "",
      presentation_title: "",
      slide_count: 5,
      include_images: true,
      speaker_notes: false,
      template_style: "corporate",
    },
  })

  const { register, handleSubmit, formState: { errors }, watch, setValue, reset } = form
  const watchedValues = watch()

  const onFileSelect = (file: File) => {
    setUploadedFile(file)
    // Clear any existing server response when new file is selected
    setServerResponse(null)
  }

  const removeFile = () => {
    setUploadedFile(null)
  }

  const clearForm = () => {
    reset()
    setUploadedFile(null)
    setServerResponse(null)
  }

  const onSubmit = async (data: CoreFormData) => {
    // Validate that we have either text or file
    if (!data.report_text.trim() && !uploadedFile) {
      toast.error("Please provide either text content or upload a file")
      return
    }

    // If no file is uploaded, validate the text meets minimum requirements
    if (!uploadedFile) {
      const textValidation = CoreFormWithTextSchema.safeParse(data)
      if (!textValidation.success) {
        const textError = textValidation.error.issues.find(e => e.path.includes('report_text'))
        if (textError) {
          toast.error(textError.message)
          return
        }
      }
    }

    setIsSubmitting(true)
    setServerResponse(null)

    try {
      // Prepare request data - file content will be read in the API layer
      const requestData = {
        report_text: data.report_text,
        presentation_title: data.presentation_title,
        slide_count: data.slide_count,
        include_images: data.include_images,
        speaker_notes: data.speaker_notes,
        template_style: data.template_style,
      }

      const response = await createPresentation(requestData, uploadedFile || undefined)
      setServerResponse(response)

      if (response.ok) {
        toast.success("Slides generated successfully!")
      }
    } catch (error) {
      console.error('Submission error:', error)
      
      if (error instanceof ApiError) {
        setServerResponse({
          ok: false,
          error: error.message,
          status: error.status,
          response: error.response,
        })
        toast.error(`Error: ${error.message}`)
      } else {
        const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred'
        setServerResponse({
          ok: false,
          error: errorMessage,
        })
        toast.error(errorMessage)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  // Content source priority: file > text (for future use)
  // const effectiveContent = uploadedFile ? `[File: ${uploadedFile.name}]` : watchedValues.report_text

  return (
    <div className={className}>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            PresGen Core - Text to Slides
          </CardTitle>
          <CardDescription>
            Transform your text content into professional slide presentations
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Content Input Section */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="report_text">
                  Report Text {!uploadedFile && <span className="text-muted-foreground text-sm">(minimum 50 characters required if no file uploaded)</span>}
                </Label>
                <Textarea
                  id="report_text"
                  placeholder={uploadedFile 
                    ? "File content will be used for presentation generation..." 
                    : "Enter your text content here (minimum 50 characters) or upload a file below..."
                  }
                  className="min-h-32"
                  {...register("report_text")}
                  disabled={!!uploadedFile}
                />
                {errors.report_text && (
                  <p className="text-sm text-destructive">{errors.report_text.message}</p>
                )}
              </div>

              <div className="relative">
                <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
                  <div className="bg-background px-2 py-1 text-xs text-muted-foreground border rounded">
                    OR
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Upload Document</Label>
                <FileDrop
                  accept={ACCEPTED_TEXT_FILES}
                  onFileSelect={onFileSelect}
                  onFileRemove={removeFile}
                  selectedFile={uploadedFile || undefined}
                  disabled={isSubmitting}
                  placeholder="Upload PDF, DOCX, or TXT file (file content takes priority)"
                />
              </div>

              {/* Markdown Preview */}
              {!uploadedFile && watchedValues.report_text && (
                <MarkdownPreview content={watchedValues.report_text} />
              )}
            </div>

            {/* Settings Section */}
            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="presentation_title">Presentation Title *</Label>
                  <Input
                    id="presentation_title"
                    placeholder="Enter presentation title"
                    {...register("presentation_title")}
                  />
                  {errors.presentation_title && (
                    <p className="text-sm text-destructive">{errors.presentation_title.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="template_style">Template Style</Label>
                  <Select
                    value={watchedValues.template_style}
                    onValueChange={(value) => setValue("template_style", value as any)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TEMPLATE_STYLES.map((style) => (
                        <SelectItem key={style.value} value={style.value}>
                          {style.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Slide Count: {watchedValues.slide_count}</Label>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground whitespace-nowrap">3 slides</span>
                    <Slider
                      value={[watchedValues.slide_count]}
                      onValueChange={(value) => setValue("slide_count", value[0])}
                      min={3}
                      max={15}
                      step={1}
                      className="flex-1"
                    />
                    <span className="text-xs text-muted-foreground whitespace-nowrap">15 slides</span>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="include_images">Include AI Images</Label>
                    <Switch
                      id="include_images"
                      checked={watchedValues.include_images}
                      onCheckedChange={(checked) => setValue("include_images", checked)}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <Label htmlFor="speaker_notes">Speaker Notes</Label>
                    <Switch
                      id="speaker_notes"
                      checked={watchedValues.speaker_notes}
                      onCheckedChange={(checked) => setValue("speaker_notes", checked)}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4 border-t">
              <Button
                type="submit"
                disabled={isSubmitting || (!watchedValues.report_text.trim() && !uploadedFile)}
                className="flex-1"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating Slides...
                  </>
                ) : (
                  "Generate Slides"
                )}
              </Button>
              
              <Button
                type="button"
                variant="outline"
                onClick={clearForm}
                disabled={isSubmitting}
              >
                Clear
              </Button>
            </div>
          </form>

          {/* Server Response */}
          {serverResponse && (
            <div className="pt-6 border-t">
              <ServerResponseCard 
                response={serverResponse} 
                title="PresGen Core Response"
              />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}