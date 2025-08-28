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
import { Textarea } from "@/components/ui/textarea"
import { FileDrop } from "./FileDrop"
import { ServerResponseCard, ServerResponse } from "./ServerResponseCard"
import { DataFormSchema, DataFormData } from "@/lib/schemas"
import { uploadDataFile, uploadReport, generateDataWithContext, ApiError } from "@/lib/api"
import { ACCEPTED_DATA_FILES, ACCEPTED_TEXT_FILES, CHART_STYLES, TEMPLATE_STYLES, UploadedDataset } from "@/lib/types"
import { toast } from "sonner"
import { BarChart3, Loader2, FileText, Eye, EyeOff } from "lucide-react"

interface DataFormProps {
  className?: string
}

export function DataForm({ className }: DataFormProps) {
  const [uploadedDataset, setUploadedDataset] = useState<UploadedDataset | null>(null)
  const [uploadedReport, setUploadedReport] = useState<{ report_id: string; filename: string; char_count?: number } | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isUploadingReport, setIsUploadingReport] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [serverResponse, setServerResponse] = useState<ServerResponse | null>(null)
  const [showMarkdownPreview, setShowMarkdownPreview] = useState(false)

  const form = useForm<DataFormData>({
    resolver: zodResolver(DataFormSchema),
    defaultValues: {
      sheet_name: "",
      has_headers: true,
      report_text: "",
      report_file: undefined,
      questions_multiline: "Which product has highest revenue?\nHow did revenue trend over time?",
      presentation_title: "",
      slide_count: 7,
      chart_style: "modern",
      include_images: true,
      speaker_notes: true,
      template_style: "corporate",
    },
  })

  const { register, handleSubmit, formState: { errors }, watch, setValue, reset } = form
  const watchedValues = watch()

  const onDataFileSelect = async (file: File) => {
    setIsUploading(true)
    setServerResponse(null)

    try {
      const response = await uploadDataFile(file)
      
      if (response.dataset_id && response.sheets) {
        const dataset: UploadedDataset = {
          dataset_id: response.dataset_id,
          sheets: response.sheets,
          original_filename: response.file_name,
          upload_time: new Date().toISOString(),
        }
        
        setUploadedDataset(dataset)
        
        // Set first sheet as default
        if (response.sheets.length > 0) {
          setValue("sheet_name", response.sheets[0])
        }
        
        toast.success("File uploaded successfully!")
      } else {
        throw new Error("Upload failed - invalid response")
      }
    } catch (error) {
      console.error('Upload error:', error)
      
      if (error instanceof ApiError) {
        toast.error(`Upload failed: ${error.message}`)
        setServerResponse({
          ok: false,
          error: error.message,
          status: error.status,
          response: error.response,
        })
      } else {
        const errorMessage = error instanceof Error ? error.message : 'Upload failed'
        toast.error(errorMessage)
        setServerResponse({
          ok: false,
          error: errorMessage,
        })
      }
    } finally {
      setIsUploading(false)
    }
  }

  const onReportFileSelect = async (file: File) => {
    setIsUploadingReport(true)
    setServerResponse(null)

    try {
      const response = await uploadReport(file)
      
      if (response.ok && response.report_id) {
        setUploadedReport({
          report_id: response.report_id,
          filename: file.name,
          char_count: response.char_count,
        })
        
        // Clear report_text when file is uploaded
        setValue("report_text", "")
        
        toast.success(`Report file uploaded successfully! (${response.char_count} characters)`)
      } else {
        throw new Error("Report upload failed - invalid response")
      }
    } catch (error) {
      console.error('Report upload error:', error)
      
      if (error instanceof ApiError) {
        toast.error(`Report upload failed: ${error.message}`)
        setServerResponse({
          ok: false,
          error: error.message,
          status: error.status,
          response: error.response,
        })
      } else {
        const errorMessage = error instanceof Error ? error.message : 'Report upload failed'
        toast.error(errorMessage)
        setServerResponse({
          ok: false,
          error: errorMessage,
        })
      }
    } finally {
      setIsUploadingReport(false)
    }
  }

  const removeDataset = () => {
    setUploadedDataset(null)
    setValue("sheet_name", "")
    setServerResponse(null)
  }

  const removeReport = () => {
    setUploadedReport(null)
    setValue("report_text", "")
    setServerResponse(null)
  }

  // Helper to parse questions from multiline textarea
  const parseQuestions = (questionsText: string): string[] => {
    return questionsText
      .split(/\r?\n/)
      .map(s => s.trim())
      .filter(Boolean)
      .slice(0, 20) // guardrail
  }

  const clearForm = () => {
    reset()
    setUploadedDataset(null)
    setUploadedReport(null)
    setServerResponse(null)
  }

  const onSubmit = async (data: DataFormData) => {
    if (!uploadedDataset) {
      toast.error("Please upload a dataset first")
      return
    }

    // Parse questions from multiline textarea
    const questions = parseQuestions(data.questions_multiline)
    if (questions.length === 0) {
      toast.error("Please add at least one question")
      return
    }

    setIsSubmitting(true)
    setServerResponse(null)

    try {
      let reportText = ""
      let reportId: string | undefined = undefined

      // Determine report context source
      if (data.report_text && data.report_text.trim()) {
        reportText = data.report_text
      } else if (uploadedReport) {
        reportId = uploadedReport.report_id
      } else {
        toast.error("Please provide report context (text or file)")
        return
      }

      const requestData = {
        dataset_id: uploadedDataset.dataset_id,
        sheet_name: data.sheet_name,
        has_headers: data.has_headers,
        questions: questions,
        report_text: reportText,
        report_id: reportId,
        presentation_title: data.presentation_title,
        slide_count: data.slide_count,
        chart_style: data.chart_style,
        include_images: data.include_images,
        speaker_notes: data.speaker_notes,
        template_style: data.template_style,
      }

      const response = await generateDataWithContext(requestData)
      setServerResponse(response)

      if (response.ok) {
        toast.success("Data slides generated successfully!")
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

  return (
    <div className={className}>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            PresGen-Data - Spreadsheet to Slides
          </CardTitle>
          <CardDescription>
            Upload spreadsheet data and generate data-driven presentations with insights and charts
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* A) Data Upload Section */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label className="text-base font-medium">A) Data Upload</Label>
                <Label>Upload Spreadsheet</Label>
                <FileDrop
                  accept={ACCEPTED_DATA_FILES}
                  onFileSelect={onDataFileSelect}
                  onFileRemove={removeDataset}
                  selectedFile={uploadedDataset ? new File([], uploadedDataset.original_filename) : undefined}
                  disabled={isUploading || isSubmitting}
                  placeholder="Upload XLSX or CSV file (max 50MB)"
                />
                {isUploading && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Processing uploaded file...
                  </div>
                )}
              </div>

              {/* Dataset Info */}
              {uploadedDataset && (
                <div className="p-3 bg-green-50 dark:bg-green-950/20 rounded-lg border border-green-200 dark:border-green-800">
                  <div className="text-sm">
                    <p className="font-medium text-green-800 dark:text-green-200">
                      Dataset Ready: {uploadedDataset.dataset_id}
                    </p>
                    <p className="text-green-600 dark:text-green-300">
                      Sheets: {uploadedDataset.sheets.join(", ")}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* B) Report Context (RAG) Section - NEW */}
            <div className="space-y-4">
              <Label className="text-base font-medium">B) Report Context (RAG)</Label>
              
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="report_text">Report Text</Label>
                    {watchedValues.report_text && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setShowMarkdownPreview(!showMarkdownPreview)}
                        disabled={isSubmitting}
                      >
                        {showMarkdownPreview ? <EyeOff className="w-3 h-3 mr-1" /> : <Eye className="w-3 h-3 mr-1" />}
                        {showMarkdownPreview ? 'Hide Preview' : 'Markdown Preview'}
                      </Button>
                    )}
                  </div>
                  {showMarkdownPreview && watchedValues.report_text ? (
                    <div className="p-3 bg-muted rounded-md prose prose-sm dark:prose-invert max-w-none">
                      <div className="whitespace-pre-wrap">{watchedValues.report_text}</div>
                    </div>
                  ) : (
                    <Textarea
                      id="report_text"
                      placeholder="Provide detailed report text that will be used as context for data insights..."
                      className="min-h-[120px]"
                      {...register("report_text")}
                      disabled={isSubmitting || !!uploadedReport}
                    />
                  )}
                </div>

                <div className="flex items-center gap-4">
                  <div className="h-px bg-border flex-1" />
                  <span className="text-sm text-muted-foreground">OR</span>
                  <div className="h-px bg-border flex-1" />
                </div>

                <div className="space-y-2">
                  <Label>Report File</Label>
                  <FileDrop
                    accept={ACCEPTED_TEXT_FILES}
                    onFileSelect={onReportFileSelect}
                    onFileRemove={removeReport}
                    selectedFile={uploadedReport ? new File([], uploadedReport.filename) : undefined}
                    disabled={isUploadingReport || isSubmitting || !!watchedValues.report_text?.trim()}
                    placeholder="Upload .txt file (max 20MB)"
                  />
                  {isUploadingReport && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Processing report file...
                    </div>
                  )}
                </div>

                {uploadedReport && (
                  <div className="p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-800">
                    <div className="text-sm">
                      <p className="font-medium text-blue-800 dark:text-blue-200 flex items-center gap-2">
                        <FileText className="w-4 h-4" />
                        Report Ready: {uploadedReport.filename}
                      </p>
                      {uploadedReport.char_count && (
                        <p className="text-blue-600 dark:text-blue-300">
                          {uploadedReport.char_count.toLocaleString()} characters extracted
                        </p>
                      )}
                    </div>
                  </div>
                )}

                <p className="text-xs text-muted-foreground">
                  Provide Report Text or upload a Report File (.txt only). If both are provided, the text will be used. PDF and DOCX files should be converted to .txt or copy-pasted directly.
                </p>
              </div>
            </div>

            {/* Configuration - only show if dataset is uploaded */}
            {uploadedDataset && (
              <>
                {/* Data configuration */}
                <div className="grid gap-6 md:grid-cols-2">
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="sheet_name">Sheet Name *</Label>
                      <Select
                        value={watchedValues.sheet_name}
                        onValueChange={(value) => setValue("sheet_name", value)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select a sheet" />
                        </SelectTrigger>
                        <SelectContent>
                          {uploadedDataset.sheets.map((sheet) => (
                            <SelectItem key={sheet} value={sheet}>
                              {sheet}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {errors.sheet_name && (
                        <p className="text-sm text-destructive">{errors.sheet_name.message}</p>
                      )}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <Label htmlFor="has_headers">Data has headers</Label>
                        <Switch
                          id="has_headers"
                          checked={watchedValues.has_headers}
                          onCheckedChange={(checked) => setValue("has_headers", checked)}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* C) Analysis & Presentation Section - ENHANCED */}
                <div className="space-y-4">
                  <Label className="text-base font-medium">C) Analysis & Presentation</Label>
                  
                  {/* Questions - Multiline */}
                  <div className="space-y-2">
                    <Label htmlFor="questions_multiline">Analysis Questions *</Label>
                    <Textarea
                      id="questions_multiline"
                      placeholder="Which product has highest revenue?\nHow did revenue trend over time?"
                      className="min-h-[100px]"
                      {...register("questions_multiline")}
                    />
                    {errors.questions_multiline && (
                      <p className="text-sm text-destructive">{errors.questions_multiline.message}</p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Enter each question on a separate line. Up to 20 questions.
                    </p>
                  </div>

                  {/* Presentation Title */}
                  <div className="space-y-2">
                    <Label htmlFor="presentation_title">Presentation Title *</Label>
                    <Input
                      id="presentation_title"
                      placeholder="e.g., Q4 2024 Sales Performance Analysis"
                      {...register("presentation_title")}
                    />
                    {errors.presentation_title && (
                      <p className="text-sm text-destructive">{errors.presentation_title.message}</p>
                    )}
                  </div>

                  {/* Controls Grid */}
                  <div className="grid gap-6 md:grid-cols-2">
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label>Slide Count: {watchedValues.slide_count}</Label>
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-muted-foreground whitespace-nowrap">3 slides</span>
                          <Slider
                            value={[watchedValues.slide_count]}
                            onValueChange={(value) => setValue("slide_count", value[0])}
                            min={3}
                            max={20}
                            step={1}
                            className="flex-1"
                          />
                          <span className="text-xs text-muted-foreground whitespace-nowrap">20 slides</span>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="chart_style">Chart Style</Label>
                        <Select
                          value={watchedValues.chart_style}
                          onValueChange={(value) => setValue("chart_style", value as "modern" | "classic" | "minimal")}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {CHART_STYLES.map((style) => (
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
                        <Label htmlFor="template_style">Template Style</Label>
                        <Select
                          value={watchedValues.template_style}
                          onValueChange={(value) => setValue("template_style", value as "corporate" | "creative" | "minimal")}
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
                  </div>

                  {/* Toggles */}
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="include_images">Include Images</Label>
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
              </>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4 border-t">
              <Button
                type="submit"
                disabled={
                  isSubmitting || 
                  !uploadedDataset || 
                  isUploading || 
                  isUploadingReport ||
                  (!watchedValues.report_text?.trim() && !uploadedReport) ||
                  !watchedValues.presentation_title?.trim() ||
                  !watchedValues.questions_multiline?.trim()
                }
                className="flex-1"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Analyzing & Generating Slides...
                  </>
                ) : (
                  "Analyze & Generate Slides"
                )}
              </Button>
              
              <Button
                type="button"
                variant="outline"
                onClick={clearForm}
                disabled={isSubmitting || isUploading || isUploadingReport}
              >
                Clear
              </Button>
            </div>
          </form>

          {/* D) Server Response Card */}
          {serverResponse && (
            <div className="pt-6 border-t">
              <ServerResponseCard 
                response={serverResponse} 
                title="PresGen-Data Response"
              />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}