'use client'

import { useState, useRef, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { 
  CheckCircle2, 
  XCircle, 
  Copy, 
  ChevronDown, 
  ChevronUp, 
  ExternalLink,
  AlertCircle 
} from "lucide-react"
import { toast } from "sonner"

export interface ServerResponse {
  ok: boolean
  message?: string
  url?: string  // Backend returns 'url' field, not 'slides_url'
  slides_url?: string  // Keep for backward compatibility
  error?: string
  // Additional response data for detailed view
  [key: string]: any
}

interface ServerResponseCardProps {
  response: ServerResponse | null
  title?: string
}

export function ServerResponseCard({ response, title = "Server Response" }: ServerResponseCardProps) {
  const [showDetails, setShowDetails] = useState(false)
  const cardRef = useRef<HTMLDivElement>(null)

  // Focus the card when response changes
  useEffect(() => {
    if (response && cardRef.current) {
      cardRef.current.focus()
      cardRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [response])

  if (!response) return null

  const isSuccess = response.ok
  const mainMessage = response.message || (isSuccess ? "Success" : response.error || "An error occurred")

  const copyToClipboard = () => {
    const jsonString = JSON.stringify(response, null, 2)
    navigator.clipboard.writeText(jsonString).then(() => {
      toast.success("Response copied to clipboard")
    }).catch(() => {
      toast.error("Failed to copy response")
    })
  }

  const openSlides = () => {
    const slidesUrl = response.url || response.slides_url
    if (slidesUrl) {
      window.open(slidesUrl, '_blank')
    }
  }

  // Filter out common fields for the details view
  const detailsData = { ...response }
  delete detailsData.ok
  delete detailsData.message
  delete detailsData.error
  delete detailsData.url
  delete detailsData.slides_url

  const hasDetails = Object.keys(detailsData).length > 0

  return (
    <Card 
      ref={cardRef}
      className="w-full focus:outline-none focus:ring-2 focus:ring-ring"
      tabIndex={-1}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            {isSuccess ? (
              <CheckCircle2 className="w-5 h-5 text-green-500" />
            ) : (
              <XCircle className="w-5 h-5 text-destructive" />
            )}
            {title}
          </CardTitle>
          
          <div className="flex items-center gap-2">
            <Badge variant={isSuccess ? "default" : "destructive"}>
              {isSuccess ? "Success" : "Error"}
            </Badge>
            
            {hasDetails && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowDetails(!showDetails)}
              >
                {showDetails ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </Button>
            )}
            
            <Button
              variant="ghost"
              size="sm"
              onClick={copyToClipboard}
            >
              <Copy className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Main message */}
        <div className="flex items-start gap-3">
          {!isSuccess && <AlertCircle className="w-4 h-4 text-destructive mt-0.5 flex-shrink-0" />}
          <p className={`text-sm ${isSuccess ? 'text-foreground' : 'text-destructive'}`}>
            {mainMessage}
          </p>
        </div>

        {/* Slides link */}
        {isSuccess && (response.url || response.slides_url) && (
          <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-950/20 rounded-lg border border-green-200 dark:border-green-800">
            <CheckCircle2 className="w-4 h-4 text-green-600" />
            <span className="text-sm text-green-800 dark:text-green-200 flex-1">
              Your slides are ready!
            </span>
            <Button
              size="sm"
              onClick={openSlides}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              <ExternalLink className="w-3 h-3 mr-1" />
              Open Slides
            </Button>
          </div>
        )}

        {/* Collapsible details */}
        {hasDetails && showDetails && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium">Response Details</h4>
              <Button
                variant="outline"
                size="sm"
                onClick={copyToClipboard}
              >
                <Copy className="w-3 h-3 mr-1" />
                Copy JSON
              </Button>
            </div>
            
            <div className="bg-muted p-3 rounded-lg text-xs font-mono overflow-auto max-h-64">
              <pre>{JSON.stringify(detailsData, null, 2)}</pre>
            </div>
          </div>
        )}

        {/* Copy action for full response */}
        <div className="flex justify-end pt-2 border-t">
          <Button
            variant="outline"
            size="sm"
            onClick={copyToClipboard}
          >
            <Copy className="w-3 h-3 mr-1" />
            Copy Full Response
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}