import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { query } = await request.json()

    if (!query || typeof query !== 'string') {
      return NextResponse.json(
        { error: 'Query is required' },
        { status: 400 }
      )
    }

    // Get API URL from environment variable (default to localhost for dev)
    const apiUrl = process.env.API_URL || 'http://localhost:8000'

    // Call the Python API server
    const response = await fetch(`${apiUrl}/api/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
      // Increase timeout for LLM calls
      signal: AbortSignal.timeout(30000), // 30 seconds
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      return NextResponse.json(
        {
          error: errorData.error || `API returned ${response.status}`,
          answer: 'Sorry, I encountered an error. Please try again later.',
        },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('API Error:', error)
    
    // Handle timeout
    if (error.name === 'TimeoutError' || error.name === 'AbortError') {
      return NextResponse.json(
        {
          error: 'Request timeout',
          answer: 'The request took too long. Please try a simpler question or try again later.',
        },
        { status: 504 }
      )
    }

    return NextResponse.json(
      {
        error: error.message || 'Internal server error',
        answer: 'Sorry, I encountered an error. Please try again later.',
        details: process.env.NODE_ENV === 'development' ? error.stack : undefined,
      },
      { status: 500 }
    )
  }
}

