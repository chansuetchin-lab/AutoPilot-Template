import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL =
  process.env.INTERNAL_API_URL ||
  'http://backend:8000'

export async function GET() {
  try {
    const response = await fetch(
      `${BACKEND_URL}/api/ai/policies`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-store',
      }
    )

    const data = await response.json()

    return NextResponse.json(data, {
      status: response.status,
    })
  } catch (error) {
    console.error(
      'Failed to fetch policies from backend:',
      error
    )

    return NextResponse.json(
      {
        detail:
          'Unable to connect to the backend policy service.',
      },
      {
        status: 502,
      }
    )
  }
}

export async function POST(
  request: NextRequest
) {
  try {
    const body = await request.json()

    const response = await fetch(
      `${BACKEND_URL}/api/ai/policies`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        cache: 'no-store',
      }
    )

    const data = await response.json()

    return NextResponse.json(data, {
      status: response.status,
    })
  } catch (error) {
    console.error(
      'Failed to create policy in backend:',
      error
    )

    return NextResponse.json(
      {
        detail:
          'Unable to connect to the backend policy service.',
      },
      {
        status: 502,
      }
    )
  }
}