import { NextRequest, NextResponse } from 'next/server'
import { readFileContent } from '@/lib/file-utils'

// Maximum file size (20MB)
const MAX_FILE_SIZE = 20 * 1024 * 1024

// Accepted file types (only text files for server-side processing)
const ACCEPTED_TYPES = [
  'text/plain'
]

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const file = formData.get('report_file') as File
    
    if (!file || file.name === 'undefined') {
      return NextResponse.json(
        { ok: false, error: 'No file provided' },
        { status: 400 }
      )
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json(
        { ok: false, error: `File size must be less than ${MAX_FILE_SIZE / (1024 * 1024)}MB` },
        { status: 400 }
      )
    }

    // Validate file type
    const fileName = file.name.toLowerCase()
    const isValidType = ACCEPTED_TYPES.includes(file.type) || fileName.endsWith('.txt')
    
    if (!isValidType) {
      return NextResponse.json(
        { ok: false, error: 'File must be .txt format. PDF and DOCX files are not supported for server-side processing.' },
        { status: 400 }
      )
    }

    // Extract text content from file
    let extractedText: string
    try {
      extractedText = await readFileContent(file)
    } catch (error) {
      console.error('Error extracting text from file:', error)
      return NextResponse.json(
        { ok: false, error: `Failed to extract text from file: ${error}` },
        { status: 400 }
      )
    }

    // Validate extracted content
    if (!extractedText || extractedText.trim().length < 10) {
      return NextResponse.json(
        { ok: false, error: 'File appears to be empty or contains insufficient text' },
        { status: 400 }
      )
    }

    // Generate a simple report ID (in a real app, you'd store this in a database)
    const reportId = `report-${Math.random().toString(36).substring(2, 11)}-${Date.now()}`
    
    // In a real application, you would store the extracted text in a database
    // For now, we'll just return the report ID and character count
    const charCount = extractedText.length

    return NextResponse.json({
      ok: true,
      report_id: reportId,
      char_count: charCount,
    })

  } catch (error) {
    console.error('Error processing report upload:', error)
    return NextResponse.json(
      { ok: false, error: 'Internal server error' },
      { status: 500 }
    )
  }
}