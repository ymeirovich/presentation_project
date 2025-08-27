'use client'

import { useState } from "react"
import { useForm, useFieldArray } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { FileDrop } from "./FileDrop"
import { ServerResponseCard, ServerResponse } from "./ServerResponseCard"
import { DataFormSchema, DataFormData } from "@/lib/schemas"
import { uploadDataFile, generateDataPresentation, ApiError } from "@/lib/api"
import { ACCEPTED_DATA_FILES, CHART_STYLES, UploadedDataset } from "@/lib/types"
import { toast } from "sonner"
import { BarChart3, Loader2, Plus, X } from "lucide-react"

interface DataFormProps {
  className?: string
}

export function DataForm({ className }: DataFormProps) {
  const [uploadedDataset, setUploadedDataset] = useState<UploadedDataset | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [serverResponse, setServerResponse] = useState<ServerResponse | null>(null)

  const form = useForm<DataFormData>({
    resolver: zodResolver(DataFormSchema),
    defaultValues: {
      sheet_name: "",
      has_headers: true,
      questions: [{ value: "" }],
      slide_count: 5,
      chart_style: "modern",
      include_data_summary: true,
    },
  })

  const { register, handleSubmit, formState: { errors }, watch, setValue, reset, control } = form
  const watchedValues = watch()

  const { fields, append, remove } = useFieldArray({
    control,
    name: "questions" as const,
  })

  const onFileSelect = async (file: File) => {
    setIsUploading(true)
    setServerResponse(null)

    try {
      const response = await uploadDataFile(file)
      
      if (response.ok && response.dataset_id && response.sheets) {
        const dataset: UploadedDataset = {
          dataset_id: response.dataset_id,
          sheets: response.sheets,
          original_filename: file.name,
          upload_time: new Date().toISOString(),
        }
        
        setUploadedDataset(dataset)
        
        // Set first sheet as default
        if (response.sheets.length > 0) {
          setValue("sheet_name", response.sheets[0])
        }
        
        toast.success("File uploaded successfully!")
      } else {
        throw new Error(response.error || "Upload failed")
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

  const removeDataset = () => {
    setUploadedDataset(null)
    setValue("sheet_name", "")
    setServerResponse(null)
  }

  const addQuestion = () => {
    append({ value: "" })
  }

  const removeQuestion = (index: number) => {
    if (fields.length > 1) {
      remove(index)
    }
  }

  const clearForm = () => {
    reset()
    setUploadedDataset(null)
    setServerResponse(null)
  }

  const onSubmit = async (data: DataFormData) => {
    if (!uploadedDataset) {
      toast.error("Please upload a dataset first")
      return
    }

    // Filter out empty questions
    const validQuestions = data.questions.filter(q => q.value.trim() !== "").map(q => q.value)
    if (validQuestions.length === 0) {
      toast.error("Please add at least one question")
      return
    }

    setIsSubmitting(true)
    setServerResponse(null)

    try {
      const requestData = {
        dataset_id: uploadedDataset.dataset_id,
        sheet_name: data.sheet_name,
        has_headers: data.has_headers,
        questions: validQuestions,
        slide_count: data.slide_count,
        chart_style: data.chart_style,
        include_data_summary: data.include_data_summary,
      }

      const response = await generateDataPresentation(requestData)
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
            {/* File Upload Section */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Upload Spreadsheet</Label>
                <FileDrop
                  accept={ACCEPTED_DATA_FILES}
                  onFileSelect={onFileSelect}
                  onFileRemove={removeDataset}
                  selectedFile={uploadedDataset ? new File([], uploadedDataset.original_filename) : undefined}
                  disabled={isUploading || isSubmitting}
                  placeholder="Upload XLSX or CSV file"
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

            {/* Configuration - only show if dataset is uploaded */}
            {uploadedDataset && (
              <>
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

                    <div className="space-y-2">
                      <Label htmlFor="chart_style">Chart Style</Label>
                      <Select
                        value={watchedValues.chart_style}
                        onValueChange={(value) => setValue("chart_style", value as any)}
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

                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <Label htmlFor="has_headers">Data has headers</Label>
                        <Switch
                          id="has_headers"
                          checked={watchedValues.has_headers}
                          onCheckedChange={(checked) => setValue("has_headers", checked)}
                        />
                      </div>

                      <div className="flex items-center justify-between">
                        <Label htmlFor="include_data_summary">Include data summary</Label>
                        <Switch
                          id="include_data_summary"
                          checked={watchedValues.include_data_summary}
                          onCheckedChange={(checked) => setValue("include_data_summary", checked)}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Questions Section */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label>Analysis Questions</Label>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={addQuestion}
                      disabled={isSubmitting}
                    >
                      <Plus className="w-3 h-3 mr-1" />
                      Add Question
                    </Button>
                  </div>

                  <div className="space-y-3">
                    {fields.map((field, index) => (
                      <div key={field.id} className="flex gap-2">
                        <div className="flex-1 space-y-1">
                          <Input
                            placeholder={`Question ${index + 1}: e.g., "What are the top 3 performing regions?"`}
                            {...register(`questions.${index}.value` as const)}
                          />
                          {errors.questions?.[index]?.value && (
                            <p className="text-sm text-destructive">
                              {errors.questions[index]?.value?.message}
                            </p>
                          )}
                        </div>
                        
                        {fields.length > 1 && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => removeQuestion(index)}
                            disabled={isSubmitting}
                          >
                            <X className="w-3 h-3" />
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                  
                  {errors.questions && (
                    <p className="text-sm text-destructive">
                      Please add at least one valid question
                    </p>
                  )}
                </div>
              </>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4 border-t">
              <Button
                type="submit"
                disabled={isSubmitting || !uploadedDataset || isUploading}
                className="flex-1"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating Data Slides...
                  </>
                ) : (
                  "Generate Data Slides"
                )}
              </Button>
              
              <Button
                type="button"
                variant="outline"
                onClick={clearForm}
                disabled={isSubmitting || isUploading}
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
                title="PresGen-Data Response"
              />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}