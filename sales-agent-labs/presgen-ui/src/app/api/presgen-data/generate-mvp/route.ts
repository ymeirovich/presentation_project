import { NextRequest, NextResponse } from 'next/server'
import { DataGenerateRequestSchema } from '@/lib/schemas'

// Backend API URL
const BACKEND_API_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // Validate request data using schema
    const validation = DataGenerateRequestSchema.safeParse(body)
    if (!validation.success) {
      return NextResponse.json(
        {
          ok: false,
          error: 'Validation failed',
          details: validation.error.errors
        },
        { status: 400 }
      )
    }

    const data = validation.data

    // In a real application, if report_id is provided, you would:
    // 1. Fetch the stored report content from database
    // 2. Replace report_id with report_text in the request
    // For this MVP, we'll just pass the request through to the backend

    // Prepare the request for the backend /data/ask endpoint
    const backendRequest = {
      dataset_id: data.dataset_id,
      sheet: data.sheet_name,
      has_headers: data.has_headers,
      questions: data.questions,
      report_text: data.report_text || '', // Use report_text or empty string
      presentation_title: data.presentation_title,
      slides: data.slide_count,
      chart_style: data.chart_style,
      include_images: data.include_images,
      speaker_notes: data.speaker_notes,
      template_style: data.template_style,
      use_cache: true,
      request_id: generateRequestId(),
    }

    // If report_id is provided instead of report_text, handle it
    if (data.report_id && !data.report_text) {
      // In a real application, fetch the report content from storage
      // For now, return an error since we don't have persistent storage
      return NextResponse.json(
        {
          ok: false,
          error: 'Report file processing not yet implemented in MVP. Please use the Report Text field instead.'
        },
        { status: 400 }
      )
    }

    // Forward the request to the backend
    const backendUrl = `${BACKEND_API_URL}/data/ask`
    
    console.log('Forwarding request to backend:', {
      url: backendUrl,
      dataset_id: backendRequest.dataset_id,
      sheet: backendRequest.sheet,
      questions_count: backendRequest.questions.length,
      report_text_length: backendRequest.report_text.length,
      presentation_title: backendRequest.presentation_title,
    })

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10 * 60 * 1000) // 10 minute timeout

    try {
      const response = await fetch(backendUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(backendRequest),
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      const responseData = await response.json()

      if (!response.ok) {
        console.error('Backend error:', response.status, responseData)
        return NextResponse.json(
          {
            ok: false,
            error: responseData.error || responseData.detail || `Backend error: ${response.status}`,
            status: response.status,
            response: responseData,
          },
          { status: response.status }
        )
      }

      // Transform the backend response to match the expected frontend schema
      const transformedResponse = {
        ok: true,
        slides_url: responseData.url || responseData.slides_url,
        message: responseData.message || 'Data slides generated successfully!'
      }

      return NextResponse.json(transformedResponse)

    } catch (fetchError) {
      clearTimeout(timeoutId)
      
      if (fetchError instanceof Error && fetchError.name === 'AbortError') {
        return NextResponse.json(
          { ok: false, error: 'Request timed out after 10 minutes' },
          { status: 408 }
        )
      }
      
      console.error('Error forwarding to backend:', fetchError)
      return NextResponse.json(
        {
          ok: false,
          error: 'Failed to connect to backend service. Please ensure the backend is running.'
        },
        { status: 502 }
      )
    }

  } catch (error) {
    console.error('Error in generate-mvp API route:', error)
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : 'Internal server error'
      },
      { status: 500 }
    )
  }
}

// Helper function to generate request ID
function generateRequestId(): string {
  return `req-${Math.random().toString(36).substring(2, 11)}-${Date.now()}`
}