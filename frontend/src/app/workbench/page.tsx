'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'

type Exception = {
  id: number
  type: string
  reason: string
  status: string
  incident?: {
    key?: string
    summary?: string
    priority?: string
    status?: string
    diagnosis?: string
    diagnosis_confidence?: number | null
    action?: string
  }
  action_result?: {
    status?: string
    message?: string
  }
  execution?: {
    status?: string
    action?: string
    issue_key?: string
    timestamp?: string
  }
  verification?: {
    status?: string
    message?: string
    reason?: string
  }
}

export default function WorkbenchPage() {
  const [exceptions, setExceptions] = useState<Exception[]>([])
  const [loading, setLoading] = useState(true)

  async function loadExceptions() {
    try {
      const data = await apiClient.get<Exception[]>(
        '/api/exceptions'
      )

      setExceptions(data)
    } catch (error) {
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadExceptions()
  }, [])

  async function approve(id: number) {
    try {
      await apiClient.post(
        `/api/exceptions/${id}/approve`
      )

      await loadExceptions()
    } catch (error) {
      console.error(error)
    }
  }

  async function reject(id: number) {
    try {
      await apiClient.post(
        `/api/exceptions/${id}/reject`
      )

      await loadExceptions()
    } catch (error) {
      console.error(error)
    }
  }

  async function remediate(id: number) {
    try {
      await apiClient.post(
        `/api/exceptions/${id}/remediate`
      )

      await loadExceptions()
    } catch (error) {
      console.error(error)
    }
  }

  async function verify(id: number) {
    try {
      await apiClient.post(
        `/api/exceptions/${id}/verify`
      )

      await loadExceptions()
    } catch (error) {
      console.error(error)
    }
  }

  function getStatusClass(status: string) {
    switch (status) {
      case 'PENDING':
        return 'text-yellow-600'

      case 'APPROVED':
        return 'text-blue-600'

      case 'REMEDIATING':
        return 'text-orange-600'

      case 'RESOLVED':
        return 'text-green-600'

      case 'REJECTED':
        return 'text-red-600'

      default:
        return 'text-gray-600'
    }
  }

  return (
    <div className="space-y-8">

      <div>
        <h1 className="text-4xl font-bold">
          AI Workbench
        </h1>

        <p className="text-muted-foreground">
          Review AI-detected exceptions and manage remediation.
        </p>
      </div>

      <div className="space-y-5">

        {loading && (
          <p>Loading exceptions...</p>
        )}

        {!loading && exceptions.length === 0 && (
          <div className="border rounded-xl p-6">
            No exceptions found.
          </div>
        )}

        {exceptions.map((item) => (
          <div
            key={item.id}
            className="border rounded-xl p-6 space-y-4"
          >

            <div className="flex items-center justify-between">

              <h2 className="text-xl font-bold">
                {item.incident?.key || `Exception #${item.id}`}
              </h2>

              <span
                className={`font-semibold ${getStatusClass(item.status)}`}
              >
                {item.status}
              </span>

            </div>

            {item.incident?.summary && (
              <p>
                <b>Summary:</b> {item.incident.summary}
              </p>
            )}

            <p>
              <b>Type:</b> {item.type}
            </p>

            <p>
              <b>Reason:</b> {item.reason}
            </p>

            {item.incident?.priority && (
              <p>
                <b>Priority:</b> {item.incident.priority}
              </p>
            )}

            {item.incident?.diagnosis && (
              <p>
                <b>Diagnosis:</b> {item.incident.diagnosis}
              </p>
            )}

            {item.incident?.action && (
              <p>
                <b>Recommended Action:</b> {item.incident.action}
              </p>
            )}

            {item.action_result && (
              <div className="border rounded-lg p-4">
                <p className="font-semibold">
                  Action Result
                </p>

                <p>
                  Status: {item.action_result.status}
                </p>

                {item.action_result.message && (
                  <p>
                    {item.action_result.message}
                  </p>
                )}
              </div>
            )}

            {item.execution && (
              <div className="border rounded-lg p-4">
                <p className="font-semibold">
                  Execution
                </p>

                <p>
                  Status: {item.execution.status}
                </p>

                <p>
                  Action: {item.execution.action}
                </p>

                {item.execution.issue_key && (
                  <p>
                    Issue: {item.execution.issue_key}
                  </p>
                )}

                {item.execution.timestamp && (
                  <p className="text-sm text-muted-foreground">
                    {item.execution.timestamp}
                  </p>
                )}
              </div>
            )}

            {item.verification && (
              <div className="border rounded-lg p-4">
                <p className="font-semibold">
                  Verification
                </p>

                <p>
                  Status: {item.verification.status}
                </p>

                {item.verification.message && (
                  <p>
                    {item.verification.message}
                  </p>
                )}

                {item.verification.reason && (
                  <p>
                    Reason: {item.verification.reason}
                  </p>
                )}
              </div>
            )}

            <div className="flex gap-3 flex-wrap">

              {item.status === 'PENDING' && (
                <>
                  <button
                    className="px-4 py-2 rounded bg-blue-600 text-white"
                    onClick={() => approve(item.id)}
                  >
                    Approve
                  </button>

                  <button
                    className="px-4 py-2 rounded bg-red-600 text-white"
                    onClick={() => reject(item.id)}
                  >
                    Reject
                  </button>
                </>
              )}

              {item.status === 'APPROVED' && (
                <button
                  className="px-4 py-2 rounded bg-orange-600 text-white"
                  onClick={() => remediate(item.id)}
                >
                  Execute Remediation
                </button>
              )}

              {item.status === 'REMEDIATING' &&
                item.verification?.status === 'PENDING' && (
                  <button
                    className="px-4 py-2 rounded bg-green-600 text-white"
                    onClick={() => verify(item.id)}
                  >
                    Verify Resolution
                  </button>
                )}

              {item.status === 'RESOLVED' && (
                <span className="px-4 py-2 rounded bg-green-100 text-green-700 font-semibold">
                  ✓ Resolved & Verified
                </span>
              )}

              {item.status === 'REJECTED' && (
                <span className="px-4 py-2 rounded bg-red-100 text-red-700 font-semibold">
                  Manual Review Required
                </span>
              )}

            </div>

          </div>
        ))}

      </div>

    </div>
  )
}
