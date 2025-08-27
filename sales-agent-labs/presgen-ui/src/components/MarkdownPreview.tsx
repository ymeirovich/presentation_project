'use client'

import { useState, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Eye, EyeOff } from "lucide-react"
import { marked } from "marked"

interface MarkdownPreviewProps {
  content: string
  className?: string
}

export function MarkdownPreview({ content, className }: MarkdownPreviewProps) {
  const [showPreview, setShowPreview] = useState(false)

  const htmlContent = useMemo(() => {
    if (!content.trim()) return ''
    
    try {
      return marked(content, {
        breaks: true,
        gfm: true,
      })
    } catch (error) {
      console.error('Markdown parsing error:', error)
      return content
    }
  }, [content])

  if (!content.trim()) return null

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">Preview</span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setShowPreview(!showPreview)}
        >
          {showPreview ? (
            <>
              <EyeOff className="w-3 h-3 mr-1" />
              Hide
            </>
          ) : (
            <>
              <Eye className="w-3 h-3 mr-1" />
              Show
            </>
          )}
        </Button>
      </div>

      {showPreview && (
        <Card>
          <CardContent className="p-4">
            <div
              className="prose prose-sm dark:prose-invert max-w-none"
              dangerouslySetInnerHTML={{ __html: htmlContent }}
              style={{
                // Custom styles for dark theme prose
                '--tw-prose-body': 'rgb(255 255 255)',
                '--tw-prose-headings': 'rgb(255 255 255)',
                '--tw-prose-lead': 'rgb(156 163 175)',
                '--tw-prose-links': 'rgb(59 130 246)',
                '--tw-prose-bold': 'rgb(255 255 255)',
                '--tw-prose-counters': 'rgb(156 163 175)',
                '--tw-prose-bullets': 'rgb(75 85 99)',
                '--tw-prose-hr': 'rgb(55 65 81)',
                '--tw-prose-quotes': 'rgb(255 255 255)',
                '--tw-prose-quote-borders': 'rgb(55 65 81)',
                '--tw-prose-captions': 'rgb(156 163 175)',
                '--tw-prose-code': 'rgb(255 255 255)',
                '--tw-prose-pre-code': 'rgb(229 231 235)',
                '--tw-prose-pre-bg': 'rgb(17 24 39)',
                '--tw-prose-th-borders': 'rgb(55 65 81)',
                '--tw-prose-td-borders': 'rgb(75 85 99)',
              } as any}
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}