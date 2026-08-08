'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import { CardWatermark } from '@/components/ui/card-watermark'
import { Icons } from '@/components/ui/icons'
import {
  InsightCard,
  type Insight,
} from '@/components/ai/insights/InsightCard'
import {
  PatternCluster,
  type Pattern,
} from '@/components/ai/insights/PatternCluster'
import {
  ActionCard,
  type ActionItem,
} from '@/components/ai/insights/ActionCard'

// ============================================================================
// Backend response types
// ============================================================================

interface BackendSummary {
  status: string
  total_tickets: number
  resolved_tickets: number
  open_tickets: number
  major_incidents: number
  human_review: number
  sla_breaches: number
  resolution_rate: number
  sla_compliance_rate: number
  human_review_rate: number
  auto_resolution_rate: number
  verification_failures: number
  verification_failure_rate: number
  average_resolution_minutes: number
  risk_level: string
  major_incidents_report: BackendMajorIncident[]
  ticket_metrics: BackendTicketMetric[]
}

interface BackendMajorIncident {
  ticket_id: string
  summary: string
  impact: string
  reasoning: string
  diagnosis: string
  recommended_action: string
}

interface BackendTicketMetric {
  ticket_id: string
  resolved: boolean
  sla_met: boolean
  human_review: boolean
  resolution_minutes: number
  summary: string
}

interface BackendRisk {
  level: string
}

interface BackendPattern {
  type: string
  severity: string
  finding: string
}

interface BackendRecommendation {
  severity: string
  title: string
  message: string
  action: string
}

interface InsightsResponse {
  status: string
  generated_at?: string | null
  summary: BackendSummary
  risk: BackendRisk
  patterns: BackendPattern[]
  recommendations: BackendRecommendation[]
  major_incidents: BackendMajorIncident[]
}

// ============================================================================
// Tabs
// ============================================================================

interface Tab {
  id: string
  label: string
  icon: React.ElementType
}

const tabs: Tab[] = [
  {
    id: 'summary',
    label: 'Summary',
    icon: Icons.activity,
  },
  {
    id: 'patterns',
    label: 'Patterns',
    icon: Icons.layers,
  },
  {
    id: 'actions',
    label: 'Actions',
    icon: Icons.zap,
  },
]

// ============================================================================
// Animations
// ============================================================================

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

// ============================================================================
// Helpers
// ============================================================================

function severityToInsightSeverity(
  severity: string
): 'critical' | 'warning' | 'info' {
  switch (severity?.toUpperCase()) {
    case 'CRITICAL':
      return 'critical'
    case 'HIGH':
    case 'WARNING':
      return 'warning'
    default:
      return 'info'
  }
}

function recommendationToActionType(
  recommendation: BackendRecommendation
): ActionItem['action_type'] {
  const text = `${recommendation.title} ${recommendation.action}`.toLowerCase()

  if (
    text.includes('policy') ||
    text.includes('automation') ||
    text.includes('automate')
  ) {
    return 'create_policy'
  }

  if (
    text.includes('transaction') ||
    text.includes('duplicate')
  ) {
    return 'review_transaction'
  }

  return 'investigate'
}

// ============================================================================
// Page
// ============================================================================

export default function AIInsightsPage() {
  const [activeTab, setActiveTab] = useState('summary')

  const [insights, setInsights] = useState<Insight[]>([])
  const [patterns, setPatterns] = useState<Pattern[]>([])
  const [actions, setActions] = useState<ActionItem[]>([])

  const [summary, setSummary] = useState<BackendSummary | null>(null)
  const [risk, setRisk] = useState<BackendRisk | null>(null)

  const [isLoading, setIsLoading] = useState(true)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const router = useRouter()

  // ========================================================================
  // Fetch REAL backend insights
  // ========================================================================

  const fetchInsights = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

      const response = await fetch(`${apiUrl}/api/insights`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-store',
      })

      if (!response.ok) {
        throw new Error(
          `Failed to fetch insights: HTTP ${response.status}`
        )
      }

      const data: InsightsResponse = await response.json()

      // ---------------------------------------------------------------
      // Store backend summary/risk
      // ---------------------------------------------------------------

      setSummary(data.summary ?? null)
      setRisk(data.risk ?? null)

      // ---------------------------------------------------------------
      // Convert major incidents -> Insight cards
      // ---------------------------------------------------------------

      const backendInsights: Insight[] = []

      for (const incident of data.major_incidents ?? []) {
        backendInsights.push({
          id: `major-${incident.ticket_id}`,
          type: 'anomaly',
          severity: 'critical',
          title: `Major Incident: ${incident.summary}`,
          description: incident.reasoning,
          data: {
            ticket_id: incident.ticket_id,
            impact: incident.impact,
            diagnosis: incident.diagnosis,
          },
          suggested_action:
            incident.recommended_action ||
            'Prioritize incident command and investigate the affected service.',
          action_type: 'investigate',
          confidence: 1,
          created_at: new Date().toISOString(),
          is_demo: false,
        })
      }

      // ---------------------------------------------------------------
      // Convert recommendations -> Insight cards
      // ---------------------------------------------------------------

      for (const recommendation of data.recommendations ?? []) {
        backendInsights.push({
          id: `recommendation-${recommendation.title}`,
          type: 'recommendation',
          severity: severityToInsightSeverity(
            recommendation.severity
          ),
          title: recommendation.title,
          description: recommendation.message,
          data: {
            action: recommendation.action,
          },
          suggested_action: recommendation.action,
          action_type: recommendationToActionType(
            recommendation
          ),
          confidence: 1,
          created_at: new Date().toISOString(),
          is_demo: false,
        })
      }

      // ---------------------------------------------------------------
      // Convert backend patterns -> PatternCluster
      // ---------------------------------------------------------------

      const backendPatterns: Pattern[] = (
        data.patterns ?? []
      ).map((pattern) => ({
        name: pattern.finding,
        frequency: pattern.type,
        confidence: 1,
        sample_size: data.summary?.total_tickets ?? 0,
        description: pattern.finding,
        is_demo: false,
      }))

      // ---------------------------------------------------------------
      // Convert recommendations -> ActionCards
      // ---------------------------------------------------------------

      const backendActions: ActionItem[] = (
        data.recommendations ?? []
      ).map((recommendation) => ({
        title: recommendation.title,
        priority:
          recommendation.severity === 'CRITICAL'
            ? 'critical'
            : recommendation.severity === 'HIGH'
              ? 'high'
              : 'medium',
        estimated_impact: recommendation.message,
        action_type: recommendationToActionType(
          recommendation
        ),
        action_config: {
          action: recommendation.action,
        },
        is_demo: false,
      }))

      setInsights(backendInsights)
      setPatterns(backendPatterns)
      setActions(backendActions)
    } catch (err) {
      console.error('AI Insights loading failed:', err)

      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load AI insights.'
      )

      setInsights([])
      setPatterns([])
      setActions([])
      setSummary(null)
      setRisk(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Initial load
  useEffect(() => {
    fetchInsights()
  }, [fetchInsights])

  // ========================================================================
  // Run Analysis
  //
  // IMPORTANT:
  // This no longer loads DEMO data.
  // It simply refreshes the real backend analysis.
  // ========================================================================

  const handleAnalyze = async () => {
    setIsAnalyzing(true)

    try {
      await fetchInsights()
    } finally {
      setIsAnalyzing(false)
    }
  }

  // ========================================================================
  // Insight actions
  // ========================================================================

  const handleInsightAction = useCallback(
    async (insight: Insight) => {
      switch (insight.action_type) {
        case 'create_policy':
          router.push('/ai/policies?tab=create-with-ai')
          break

        case 'investigate':
        case 'review_duplicate':
        case 'review_transaction':
          router.push('/workbench')
          break

        default:
          router.push('/workbench')
          break
      }
    },
    [router]
  )

  const handleDismissInsight = useCallback(
    async (id: string) => {
      setInsights((prev) =>
        prev.filter((insight) => insight.id !== id)
      )
    },
    []
  )

  const handleApplyAction = useCallback(
    async (action: ActionItem) => {
      switch (action.action_type) {
        case 'create_policy':
          router.push('/ai/policies?tab=create-with-ai')
          break

        case 'investigate':
        case 'review_transaction':
          router.push('/workbench')
          break

        default:
          router.push('/workbench')
          break
      }
    },
    [router]
  )

  // ========================================================================
  // Statistics
  // ========================================================================

  const criticalCount = insights.filter(
    (i) => i.severity === 'critical'
  ).length

  const warningCount = insights.filter(
    (i) => i.severity === 'warning'
  ).length

  const infoCount = insights.filter(
    (i) => i.severity === 'info'
  ).length

  const riskLevel =
    risk?.level ||
    summary?.risk_level ||
    'UNKNOWN'

  // ========================================================================
  // Render
  // ========================================================================

  return (
    <motion.div
      className="space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <motion.div
        variants={itemVariants}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-brand-navy">
            AI Insights
          </h1>

          <p className="mt-1 text-sm text-muted-foreground">
            AI-powered analysis of your incident data, SLA
            performance, remediation and operational risk.
          </p>
        </div>

        <Button
          variant="gradient"
          onClick={handleAnalyze}
          disabled={isAnalyzing || isLoading}
        >
          {isAnalyzing ? (
            <>
              <Icons.loader className="mr-2 h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Icons.sparkles
                className="mr-2 h-4 w-4"
                strokeWidth={1.5}
              />
              Run Analysis
            </>
          )}
        </Button>
      </motion.div>

      {/* Backend connection / risk status */}
      <motion.div
        variants={itemVariants}
        className="rounded-lg border p-4"
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'h-3 w-3 rounded-full',
                error
                  ? 'bg-red-500'
                  : 'bg-green-500'
              )}
            />

            <div>
              <p className="font-medium text-brand-navy">
                {error
                  ? 'AI backend connection failed'
                  : 'Live AI backend connected'}
              </p>

              <p className="text-sm text-muted-foreground">
                {error
                  ? error
                  : 'Insights are generated from the current incident data.'}
              </p>
            </div>
          </div>

          {!error && (
            <div className="text-right">
              <p className="text-xs text-muted-foreground">
                Risk Level
              </p>

              <p
                className={cn(
                  'font-bold',
                  riskLevel === 'CRITICAL'
                    ? 'text-red-600'
                    : riskLevel === 'HIGH'
                      ? 'text-orange-600'
                      : riskLevel === 'MEDIUM'
                        ? 'text-amber-600'
                        : 'text-green-600'
                )}
              >
                {riskLevel}
              </p>
            </div>
          )}
        </div>
      </motion.div>

      {/* Stats */}
      <motion.div
        variants={itemVariants}
        className="grid gap-4 sm:grid-cols-3"
      >
        <Card className="relative overflow-hidden">
          <CardWatermark opacity={2} scale={0.8} />

          <CardContent className="relative z-10 flex items-center gap-4 py-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-100">
              <Icons.alertCircle
                className="h-6 w-6 text-red-600"
                strokeWidth={1.5}
              />
            </div>

            <div>
              <p className="text-2xl font-bold text-brand-navy">
                {criticalCount}
              </p>

              <p className="text-sm text-muted-foreground">
                Critical Issues
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <CardWatermark opacity={2} scale={0.8} />

          <CardContent className="relative z-10 flex items-center gap-4 py-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-100">
              <Icons.alertTriangle
                className="h-6 w-6 text-amber-600"
                strokeWidth={1.5}
              />
            </div>

            <div>
              <p className="text-2xl font-bold text-brand-navy">
                {warningCount}
              </p>

              <p className="text-sm text-muted-foreground">
                Warnings
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <CardWatermark opacity={2} scale={0.8} />

          <CardContent className="relative z-10 flex items-center gap-4 py-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
              <Icons.lightbulb
                className="h-6 w-6 text-blue-600"
                strokeWidth={1.5}
              />
            </div>

            <div>
              <p className="text-2xl font-bold text-brand-navy">
                {infoCount + patterns.length}
              </p>

              <p className="text-sm text-muted-foreground">
                Recommendations
              </p>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Operational metrics */}
      {summary && (
        <motion.div
          variants={itemVariants}
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">
                Tickets
              </p>

              <p className="mt-1 text-2xl font-bold">
                {summary.total_tickets}
              </p>

              <p className="mt-1 text-xs text-muted-foreground">
                {summary.open_tickets} open
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">
                SLA Compliance
              </p>

              <p className="mt-1 text-2xl font-bold">
                {summary.sla_compliance_rate}%
              </p>

              <p className="mt-1 text-xs text-muted-foreground">
                {summary.sla_breaches} SLA breaches
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">
                Human Review
              </p>

              <p className="mt-1 text-2xl font-bold">
                {summary.human_review_rate}%
              </p>

              <p className="mt-1 text-xs text-muted-foreground">
                {summary.human_review} tickets
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">
                Auto Resolution
              </p>

              <p className="mt-1 text-2xl font-bold">
                {summary.auto_resolution_rate}%
              </p>

              <p className="mt-1 text-xs text-muted-foreground">
                {summary.verification_failures} verification failures
              </p>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Tabs */}
      <motion.div variants={itemVariants}>
        <div
          className={cn(
            'inline-flex items-center gap-1 rounded-xl p-1',
            'bg-white/50 border border-border/50',
            'backdrop-blur-sm'
          )}
        >
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id
            const Icon = tab.icon

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'relative flex items-center gap-2 rounded-lg px-4 py-2.5',
                  'text-sm font-medium transition-all duration-200',
                  'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-cornflower/50',
                  isActive
                    ? 'text-white'
                    : 'text-muted-foreground hover:text-foreground hover:bg-white/50'
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeInsightTab"
                    className="absolute inset-0 rounded-lg bg-brand-navy shadow-soft"
                    transition={{
                      type: 'spring',
                      stiffness: 400,
                      damping: 30,
                    }}
                  />
                )}

                <span className="relative z-10 flex items-center gap-2">
                  <Icon
                    className="h-4 w-4"
                    strokeWidth={1.5}
                  />

                  <span className="hidden sm:inline">
                    {tab.label}
                  </span>
                </span>
              </button>
            )
          })}
        </div>
      </motion.div>

      {/* Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
        >
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Icons.loader
                className="h-8 w-8 animate-spin text-brand-cornflower"
              />
            </div>
          ) : (
            <>
              {/* Summary */}
              {activeTab === 'summary' && (
                <Card className="relative overflow-hidden">
                  <CardWatermark opacity={2} scale={1} />

                  <CardHeader className="relative z-10">
                    <CardTitle>Live AI Analysis</CardTitle>

                    <CardDescription>
                      {insights.length} insights generated from the
                      current backend analysis.
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="relative z-10 space-y-4">
                    {insights.length === 0 ? (
                      <div className="flex flex-col items-center justify-center py-12 text-center">
                        <Icons.lightbulb className="mb-4 h-8 w-8 text-brand-cornflower" />

                        <h3 className="font-display text-lg font-semibold text-brand-navy">
                          No insights available
                        </h3>

                        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                          Run the analysis again after adding or updating
                          incident data.
                        </p>
                      </div>
                    ) : (
                      insights.map((insight) => (
                        <InsightCard
                          key={insight.id}
                          insight={insight}
                          onAction={handleInsightAction}
                          onDismiss={handleDismissInsight}
                        />
                      ))
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Patterns */}
              {activeTab === 'patterns' && (
                <Card className="relative overflow-hidden">
                  <CardWatermark opacity={2} scale={1} />

                  <CardHeader className="relative z-10">
                    <CardTitle>
                      Detected Operational Patterns
                    </CardTitle>

                    <CardDescription>
                      Patterns detected from the live incident analysis.
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="relative z-10">
                    {patterns.length > 0 ? (
                      <PatternCluster patterns={patterns} />
                    ) : (
                      <p className="py-8 text-center text-sm text-muted-foreground">
                        No patterns detected.
                      </p>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Actions */}
              {activeTab === 'actions' && (
                <Card className="relative overflow-hidden">
                  <CardWatermark opacity={2} scale={1} />

                  <CardHeader className="relative z-10">
                    <CardTitle>
                      Recommended Actions
                    </CardTitle>

                    <CardDescription>
                      Actions generated from the live operational analysis.
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="relative z-10 space-y-3">
                    {actions.length === 0 ? (
                      <div className="flex flex-col items-center justify-center py-12 text-center">
                        <Icons.zap className="mb-4 h-6 w-6 text-muted-foreground" />

                        <p className="text-sm text-muted-foreground">
                          No actions recommended at this time.
                        </p>
                      </div>
                    ) : (
                      actions.map((action, idx) => (
                        <ActionCard
                          key={`${action.title}-${idx}`}
                          action={action}
                          onApply={handleApplyAction}
                        />
                      ))
                    )}
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </motion.div>
      </AnimatePresence>
    </motion.div>
  )
}