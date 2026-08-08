'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { CardWatermark } from '@/components/ui/card-watermark'
import { Icons } from '@/components/ui/icons'
import {
  PolicyCard,
  type Policy,
} from '@/components/ai/policies/PolicyCard'
import { PolicyDetailModal } from '@/components/ai/policies/PolicyDetailModal'
import { PolicyEditModal } from '@/components/ai/policies/PolicyEditModal'
import { CreateWithAI } from '@/components/ai/policies/CreateWithAI'
import { PermissionMatrixTab } from '@/components/ai/policies/PermissionMatrixTab'
import { StructuredBuilder } from '@/components/ai/policies/StructuredBuilder'
import { apiClient } from '@/lib/api-client'

// ============================================================================
// Types
// ============================================================================

type TabType =
  | 'policies'
  | 'create-ai'
  | 'structured'
  | 'matrix'

type FilterType =
  | 'all'
  | 'active'
  | 'inactive'
  | 'logical'
  | 'natural_language'

type SortType =
  | 'newest'
  | 'oldest'
  | 'priority'
  | 'name'
  | 'executions'

type StructuredDSL = {
  conditions: Array<{
    field: string
    operator: string
    value: string
  }>
  actions: Array<{
    type: string
    value?: string
  }>
  match_mode: 'all' | 'any'
}

// ============================================================================
// Animation Variants
// ============================================================================

const containerVariants = {
  hidden: {
    opacity: 0,
  },

  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
    },
  },
}

const itemVariants = {
  hidden: {
    opacity: 0,
    y: 20,
  },

  visible: {
    opacity: 1,
    y: 0,
  },
}

// ============================================================================
// Tabs
// ============================================================================

const TABS = [
  {
    id: 'policies' as TabType,
    label: 'Policies',
    Icon: Icons.layers,
  },
  {
    id: 'create-ai' as TabType,
    label: 'Create with AI',
    Icon: Icons.sparkles,
  },
  {
    id: 'structured' as TabType,
    label: 'Structured Builder',
    Icon: Icons.grid,
  },
  {
    id: 'matrix' as TabType,
    label: 'Permission Matrix',
    Icon: Icons.table,
  },
]

// ============================================================================
// API helper
// ============================================================================

async function fetchPoliciesFromAPI(): Promise<Policy[]> {
  const data = await apiClient.get<Policy[]>(
    '/api/ai/policies'
  )

  console.log('[POLICY DEBUG] API returned:', data)
  console.log(
    '[POLICY DEBUG] Is array:',
    Array.isArray(data)
  )
  console.log(
    '[POLICY DEBUG] Count:',
    Array.isArray(data) ? data.length : 'N/A'
  )


  if (!Array.isArray(data)) {
    console.warn(
      'Policy API returned a non-array response:',
      data
    )

    return []
  }

  return data
}

// ============================================================================
// Create policy API
// ============================================================================

async function createPolicyFromAPI(policyData: {
  name: string
  description: string
  natural_language: string
  policy_type: 'logical' | 'natural_language'
  policy_scope?: 'base' | 'instruction' | 'custom'
  dsl: unknown
  refined_instruction: string | null
  ai_instruction: string | null
  entity_name: string | null
  is_active?: boolean
  priority: number
  tags: string[]
  source?: string
}): Promise<Policy> {
  return apiClient.post<Policy>(
    '/api/ai/policies',
    policyData
  )
}

// ============================================================================
// Page
// ============================================================================

export default function AIPoliciesPage() {
  // --------------------------------------------------------------------------
  // Policy state
  // --------------------------------------------------------------------------

  const [policies, setPolicies] = useState<Policy[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  // --------------------------------------------------------------------------
  // Tab state
  // --------------------------------------------------------------------------

  const [activeTab, setActiveTab] =
    useState<TabType>('policies')

  // --------------------------------------------------------------------------
  // Modal state
  // --------------------------------------------------------------------------

  const [selectedPolicy, setSelectedPolicy] =
    useState<Policy | null>(null)

  const [isDetailModalOpen, setIsDetailModalOpen] =
    useState(false)

  const [editingPolicy, setEditingPolicy] =
    useState<Policy | null>(null)

  const [isEditModalOpen, setIsEditModalOpen] =
    useState(false)

  // --------------------------------------------------------------------------
  // Filter state
  // --------------------------------------------------------------------------

  const [filter, setFilter] =
    useState<FilterType>('all')

  const [sortBy, setSortBy] =
    useState<SortType>('newest')

  const [searchQuery, setSearchQuery] =
    useState('')

  // --------------------------------------------------------------------------
  // Structured builder state
  // --------------------------------------------------------------------------

  const [structuredDSL, setStructuredDSL] =
    useState<StructuredDSL | null>(null)

  const [structuredName, setStructuredName] =
    useState('')

  const [isSavingStructured, setIsSavingStructured] =
    useState(false)

  // --------------------------------------------------------------------------
  // Create state
  // --------------------------------------------------------------------------

  const [isCreatingPolicy, setIsCreatingPolicy] =
    useState(false)

  const [createError, setCreateError] =
    useState<string | null>(null)

  // ==========================================================================
  // Load Policies
  // ==========================================================================

  const loadPolicies = useCallback(async () => {
    setIsLoading(true)
    setLoadError(null)

    try {
      const data = await fetchPoliciesFromAPI()
      console.log('[POLICY DEBUG] Setting policies:', data)
      setPolicies(data)
    } catch (error) {
      console.error(
        'Failed to load policies:',
        error
      )

      setLoadError(
        error instanceof Error
          ? error.message
          : 'Unable to load policies.'
      )

      setPolicies([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadPolicies()
  }, [loadPolicies])

  // ==========================================================================
  // Policy Actions
  // ==========================================================================

  const handleCardClick = useCallback(
    (policy: Policy) => {
      setSelectedPolicy(policy)
      setIsDetailModalOpen(true)
    },
    []
  )

  const handleEditFromDetail = useCallback(
    (policy: Policy) => {
      setEditingPolicy(policy)
      setIsDetailModalOpen(false)
      setIsEditModalOpen(true)
    },
    []
  )

  const handleSavePolicy = useCallback(async () => {
    setIsEditModalOpen(false)
    setEditingPolicy(null)

    await loadPolicies()
  }, [loadPolicies])

  // --------------------------------------------------------------------------
  // Toggle
  //
  // Backend PATCH endpoint is not implemented yet.
  // This remains a local UI update for now.
  // --------------------------------------------------------------------------

  const togglePolicyStatus = useCallback(
    async (
      id: string,
      isActive: boolean
    ) => {
      setPolicies(
        (previousPolicies) =>
          previousPolicies.map(
            (policy) =>
              policy.id === id
                ? {
                    ...policy,
                    is_active: !isActive,
                  }
                : policy
          )
      )
    },
    []
  )

  // --------------------------------------------------------------------------
  // Delete
  //
  // Backend DELETE endpoint is not implemented yet.
  // This remains a local UI update for now.
  // --------------------------------------------------------------------------

  const deletePolicy = useCallback(
    async (id: string) => {
      setPolicies(
        (previousPolicies) =>
          previousPolicies.filter(
            (policy) =>
              policy.id !== id
          )
      )
    },
    []
  )

  // ==========================================================================
  // Create Policy
  // ==========================================================================

  const handlePolicyCreate = useCallback(
    async (policyData: {
      name: string
      description: string
      naturalLanguage: string
      policyType:'logical' | 'natural_language'
      dsl: unknown
      refinedInstruction: string | null
      entityName: string | null
      tags: string[]
      priority: number
    }) => {

      console.log(
        '🚀 handlePolicyCreate CALLED:',
        policyData
      )

      setIsCreatingPolicy(true)
      setCreateError(null)

      try {
        // Convert frontend field names to the backend
        // PolicyCreate schema.
        const backendPolicy = {
          name: policyData.name,

          description:
            policyData.description,

          natural_language:
            policyData.naturalLanguage,

          summary:
            policyData.description ||
            policyData.name,

          policy_type:
            policyData.policyType,

          policy_scope: 'base' as const,

          dsl:
            policyData.dsl,

          refined_instruction:
            policyData.refinedInstruction,

          ai_instruction:
            policyData.naturalLanguage,

          entity_name:
            policyData.entityName,

          is_active: true,

          priority:
            policyData.priority,

          tags:
            policyData.tags,

          source: 'user',
        }
        console.log(
          '[POLICY CREATE] Sending to backend:',
          backendPolicy
        )

        await createPolicyFromAPI(
          backendPolicy
        )

        console.log(
          '[POLICY CREATE] Backend save completed'
        )

        // Reload the actual database records.
        await loadPolicies()

        // Return to policy list.
        setActiveTab('policies')
      } catch (error) {
        console.error(
          'Failed to create policy:',
          error
        )

        const message =
          error instanceof Error
            ? error.message
            : 'Unable to create policy.'

        setCreateError(message)

        throw error
      } finally {
        setIsCreatingPolicy(false)
      }
    },
    [loadPolicies]
  )

  // ==========================================================================
  // Filtering
  // ==========================================================================

  const filteredPolicies = policies
    .filter((policy) => {
      // Active / inactive
      if (
        filter === 'active' &&
        !policy.is_active
      ) {
        return false
      }

      if (
        filter === 'inactive' &&
        policy.is_active
      ) {
        return false
      }

      // Policy type
      if (
        filter === 'logical' &&
        policy.policy_type !== 'logical'
      ) {
        return false
      }

      if (
        filter ===
          'natural_language' &&
        policy.policy_type !==
          'natural_language'
      ) {
        return false
      }

      // Search
      if (searchQuery.trim()) {
        const query =
          searchQuery
            .toLowerCase()
            .trim()

        const matchesName =
          policy.name
            ?.toLowerCase()
            .includes(query)

        const matchesDescription =
          policy.description
            ?.toLowerCase()
            .includes(query)

        const matchesNaturalLanguage =
          policy.natural_language
            ?.toLowerCase()
            .includes(query)

        const matchesTags =
          policy.tags?.some(
            (tag) =>
              tag
                .toLowerCase()
                .includes(query)
          )

        if (
          !matchesName &&
          !matchesDescription &&
          !matchesNaturalLanguage &&
          !matchesTags
        ) {
          return false
        }
      }

      return true
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'newest':
          return (
            new Date(
              b.created_at
            ).getTime() -
            new Date(
              a.created_at
            ).getTime()
          )

        case 'oldest':
          return (
            new Date(
              a.created_at
            ).getTime() -
            new Date(
              b.created_at
            ).getTime()
          )

        case 'priority':
          return (
            a.priority -
            b.priority
          )

        case 'name':
          return a.name.localeCompare(
            b.name
          )

        case 'executions':
          return (
            b.execution_count -
            a.execution_count
          )

        default:
          return 0
      }
    })

  // ==========================================================================
  // Stats
  // ==========================================================================

  const stats = {
    total: policies.length,

    active: policies.filter(
      (policy) =>
        policy.is_active
    ).length,

    structured: policies.filter(
      (policy) =>
        policy.policy_type ===
        'logical'
    ).length,

    natural: policies.filter(
      (policy) =>
        policy.policy_type ===
        'natural_language'
    ).length,
  }

  // ==========================================================================
  // Render
  // ==========================================================================

  return (
    <motion.div
      className="space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* ================================================================== */}
      {/* Header */}
      {/* ================================================================== */}

      <motion.div
        variants={itemVariants}
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4"
      >
        <div>
          <h1 className="text-2xl font-bold text-brand-navy">
            AI Policies
          </h1>

          <p className="mt-1 text-sm text-muted-foreground">
            Define business rules in natural
            language. The AI determines the
            best format.
          </p>
        </div>

        <Button
          variant="gradient"
          onClick={() =>
            setActiveTab('create-ai')
          }
        >
          <Icons.plus className="mr-2 h-4 w-4" />
          Create Policy
        </Button>
      </motion.div>

      {/* ================================================================== */}
      {/* Create Error */}
      {/* ================================================================== */}

      {createError && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="flex items-center justify-between gap-4 p-4">
            <div>
              <p className="font-medium text-red-700">
                Unable to create policy
              </p>

              <p className="mt-1 text-sm text-red-600">
                {createError}
              </p>
            </div>

            <Button
              variant="outline"
              onClick={() =>
                setCreateError(null)
              }
            >
              Dismiss
            </Button>
          </CardContent>
        </Card>
      )}

      {/* ================================================================== */}
      {/* Tabs */}
      {/* ================================================================== */}

      <motion.div variants={itemVariants}>
        <div className="flex flex-wrap gap-1 p-1.5 bg-gray-100 rounded-xl">
          {TABS.map((tab) => (
            <motion.button
              key={tab.id}
              type="button"
              onClick={() =>
                setActiveTab(tab.id)
              }
              className={cn(
                'relative flex items-center gap-2 px-4 py-2.5 rounded-lg',
                'text-sm font-medium transition-colors',
                activeTab === tab.id
                  ? 'text-brand-navy'
                  : 'text-muted-foreground hover:text-foreground'
              )}
              whileHover={{
                scale:
                  activeTab === tab.id
                    ? 1
                    : 1.02,
              }}
              whileTap={{
                scale: 0.98,
              }}
            >
              {activeTab === tab.id && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute inset-0 bg-white rounded-lg shadow-sm"
                  transition={{
                    type: 'spring',
                    stiffness: 500,
                    damping: 35,
                  }}
                />
              )}

              <span className="relative z-10 flex items-center gap-2">
                <tab.Icon className="h-4 w-4" />

                {tab.label}
              </span>
            </motion.button>
          ))}
        </div>
      </motion.div>

      {/* ================================================================== */}
      {/* Tab Content */}
      {/* ================================================================== */}

      <AnimatePresence mode="popLayout">
        {/* ================================================================ */}
        {/* POLICIES */}
        {/* ================================================================ */}

        {activeTab === 'policies' && (
          <motion.div
            key="policies-tab"
            initial={false}
            animate={{
              opacity: 1,
              y: 0,
            }}
            exit={{
              opacity: 0,
              y: -10,
            }}
            transition={{
              duration: 0.15,
            }}
            className="space-y-6"
          >
            {/* ========================================================== */}
            {/* Stats */}
            {/* ========================================================== */}

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                {
                  value: stats.total,
                  label: 'Total Policies',
                  icon: Icons.layers,
                  bg: 'bg-brand-navy/10',
                  color: 'text-brand-navy',
                },
                {
                  value: stats.active,
                  label: 'Active',
                  icon: Icons.check,
                  bg: 'bg-emerald-100',
                  color: 'text-emerald-600',
                },
                {
                  value: stats.structured,
                  label: 'Structured',
                  icon: Icons.grid,
                  bg: 'bg-blue-100',
                  color: 'text-blue-600',
                },
                {
                  value: stats.natural,
                  label: 'Natural Language',
                  icon: Icons.brain,
                  bg: 'bg-purple-100',
                  color: 'text-purple-600',
                },
              ].map((stat) => (
                <motion.div
                  key={stat.label}
                  className="bg-white rounded-xl border border-gray-200 p-4 hover:border-gray-300 hover:shadow-md transition-all cursor-default"
                  whileHover={{
                    y: -2,
                    boxShadow:
                      '0 4px 12px rgba(0,0,0,0.1)',
                  }}
                >
                  <div className="flex items-center gap-3">
                    <motion.div
                      className={cn(
                        'p-2 rounded-lg',
                        stat.bg
                      )}
                      whileHover={{
                        scale: 1.1,
                        rotate: 5,
                      }}
                      transition={{
                        type: 'spring',
                        stiffness: 400,
                      }}
                    >
                      <stat.icon
                        className={cn(
                          'h-5 w-5',
                          stat.color
                        )}
                      />
                    </motion.div>

                    <div>
                      <p
                        className={cn(
                          'text-2xl font-bold',
                          stat.color
                        )}
                      >
                        {stat.value}
                      </p>

                      <p className="text-xs text-muted-foreground">
                        {stat.label}
                      </p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* ========================================================== */}
            {/* Error */}
            {/* ========================================================== */}

            {loadError && (
              <Card className="border-red-200 bg-red-50">
                <CardContent className="flex items-center justify-between gap-4 p-4">
                  <div>
                    <p className="font-medium text-red-700">
                      Unable to load policies
                    </p>

                    <p className="mt-1 text-sm text-red-600">
                      {loadError}
                    </p>
                  </div>

                  <Button
                    variant="outline"
                    onClick={loadPolicies}
                  >
                    Retry
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* ========================================================== */}
            {/* Search / Filters */}
            {/* ========================================================== */}

            <motion.div
              variants={itemVariants}
              className="flex flex-col sm:flex-row gap-4"
            >
              {/* Search */}

              <div className="relative flex-1">
                <Icons.search
                  className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground"
                />

                <input
                  type="text"
                  value={searchQuery}
                  onChange={(event) =>
                    setSearchQuery(
                      event.target.value
                    )
                  }
                  placeholder="Search policies..."
                  className={cn(
                    'w-full pl-10 pr-4 py-2.5 rounded-lg',
                    'border border-input bg-white',
                    'text-sm focus:outline-none',
                    'focus:ring-2 focus:ring-brand-cornflower/50'
                  )}
                />
              </div>

              {/* Filter */}

              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground whitespace-nowrap">
                  Filter:
                </span>

                <select
                  value={filter}
                  onChange={(event) =>
                    setFilter(
                      event.target
                        .value as FilterType
                    )
                  }
                  className="px-3 py-2.5 rounded-lg border border-input bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-cornflower/50"
                >
                  <option value="all">
                    All
                  </option>

                  <option value="active">
                    Active
                  </option>

                  <option value="inactive">
                    Inactive
                  </option>

                  <option value="logical">
                    Structured
                  </option>

                  <option value="natural_language">
                    Natural Language
                  </option>
                </select>
              </div>

              {/* Sort */}

              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground whitespace-nowrap">
                  Sort:
                </span>

                <select
                  value={sortBy}
                  onChange={(event) =>
                    setSortBy(
                      event.target
                        .value as SortType
                    )
                  }
                  className="px-3 py-2.5 rounded-lg border border-input bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-cornflower/50"
                >
                  <option value="newest">
                    Newest
                  </option>

                  <option value="oldest">
                    Oldest
                  </option>

                  <option value="priority">
                    Priority
                  </option>

                  <option value="name">
                    Name
                  </option>

                  <option value="executions">
                    Most Used
                  </option>
                </select>
              </div>
            </motion.div>

            {/* ========================================================== */}
            {/* Policy Grid */}
            {/* ========================================================== */}

            <motion.div variants={itemVariants}>
              {isLoading ? (
                <div className="flex items-center justify-center py-16">
                  <Icons.loader className="h-8 w-8 animate-spin text-brand-cornflower" />
                </div>
              ) : filteredPolicies.length === 0 ? (
                <Card className="relative overflow-hidden">
                  <CardWatermark
                    opacity={3}
                    scale={1}
                  />

                  <CardContent className="relative z-10 flex flex-col items-center justify-center py-16 text-center">
                    <div
                      className={cn(
                        'mb-4 flex h-16 w-16 items-center justify-center rounded-2xl',
                        'bg-gradient-to-br from-brand-cornflower/20 to-brand-purple/20'
                      )}
                    >
                      <Icons.brain
                        className="h-8 w-8 text-brand-cornflower"
                        strokeWidth={1.5}
                      />
                    </div>

                    <h3 className="font-display text-lg font-semibold text-brand-navy">
                      {searchQuery ||
                      filter !== 'all'
                        ? 'No matching policies'
                        : 'No policies yet'}
                    </h3>

                    <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                      {searchQuery ||
                      filter !== 'all'
                        ? 'Try adjusting your search or filter criteria.'
                        : 'Create your first AI policy using natural language.'}
                    </p>

                    <Button
                      variant="gradient"
                      className="mt-6"
                      onClick={() =>
                        setActiveTab(
                          'create-ai'
                        )
                      }
                    >
                      <Icons.sparkles className="mr-2 h-4 w-4" />
                      Create with AI
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {filteredPolicies.map(
                    (policy) => (
                      <PolicyCard
                        key={policy.id}
                        policy={policy}
                        onClick={
                          handleCardClick
                        }
                      />
                    )
                  )}
                </div>
              )}
            </motion.div>
          </motion.div>
        )}

        {/* ================================================================ */}
        {/* CREATE WITH AI */}
        {/* ================================================================ */}

        {activeTab === 'create-ai' && (
          <motion.div
            key="create-ai-tab"
            initial={{
              opacity: 0,
              x: 20,
            }}
            animate={{
              opacity: 1,
              x: 0,
            }}
            exit={{
              opacity: 0,
              x: -20,
            }}
            transition={{
              duration: 0.15,
            }}
          >
            <Card className="relative overflow-hidden">
              <CardWatermark
                opacity={2}
                scale={1}
              />

              <CardContent className="relative z-10 py-8">
                <CreateWithAI
                  onPolicyCreate={
                    handlePolicyCreate
                  }
                  onCancel={() =>
                    setActiveTab(
                      'policies'
                    )
                  }
                />
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* ================================================================ */}
        {/* STRUCTURED BUILDER */}
        {/* ================================================================ */}

        {activeTab === 'structured' && (
          <motion.div
            key="structured-tab"
            initial={{
              opacity: 0,
              x: 20,
            }}
            animate={{
              opacity: 1,
              x: 0,
            }}
            exit={{
              opacity: 0,
              x: -20,
            }}
            transition={{
              duration: 0.15,
            }}
          >
            <Card className="relative overflow-hidden">
              <CardWatermark
                opacity={2}
                scale={1}
              />

              <CardContent className="relative z-10 py-8">
                <div className="max-w-3xl mx-auto">
                  <div className="text-center mb-8">
                    <h2 className="text-xl font-bold text-brand-navy mb-2">
                      Structured Rule Builder
                    </h2>

                    <p className="text-muted-foreground">
                      Visually build rules with
                      conditions and actions
                    </p>
                  </div>

                  {/* Rule name */}

                  <div className="mb-6">
                    <label className="block text-sm font-medium text-foreground mb-1.5">
                      Rule Name *
                    </label>

                    <input
                      type="text"
                      value={structuredName}
                      onChange={(event) =>
                        setStructuredName(
                          event.target.value
                        )
                      }
                      placeholder="e.g., Auto-Approve Low Value Items"
                      className="w-full px-4 py-2.5 rounded-lg border border-gray-200 text-base focus:outline-none focus:ring-2 focus:ring-brand-cornflower/50"
                    />
                  </div>

                  {/* Builder */}

                  <StructuredBuilder
                    onChange={(dsl) =>
                      setStructuredDSL(
                        dsl as StructuredDSL
                      )
                    }
                  />

                  {/* Buttons */}

                  <div className="flex justify-center gap-3 mt-8">
                    <Button
                      variant="ghost"
                      onClick={() => {
                        setStructuredName('')
                        setStructuredDSL(null)
                        setCreateError(null)
                        setActiveTab(
                          'policies'
                        )
                      }}
                    >
                      Cancel
                    </Button>

                    <Button
                      variant="gradient"
                      disabled={
                        !structuredDSL ||
                        structuredDSL
                          .conditions
                          .length === 0 ||
                        !structuredName.trim() ||
                        isSavingStructured ||
                        isCreatingPolicy
                      }
                      onClick={async () => {
                        if (
                          !structuredDSL ||
                          !structuredName.trim()
                        ) {
                          return
                        }

                        setIsSavingStructured(
                          true
                        )

                        try {
                          await handlePolicyCreate(
                            {
                              name:
                                structuredName.trim(),

                              description:
                                '',

                              naturalLanguage:
                                `Structured rule: ${structuredName.trim()}`,

                              policyType:
                                'logical',

                              dsl: {
                                conditions:
                                  structuredDSL.conditions.map(
                                    (
                                      condition
                                    ) => ({
                                      field:
                                        condition.field,

                                      operator:
                                        condition.operator,

                                      value:
                                        condition.value,
                                    })
                                  ),

                                actions:
                                  structuredDSL.actions.map(
                                    (
                                      action
                                    ) => ({
                                      type:
                                        action.type,

                                      value:
                                        action.value,
                                    })
                                  ),

                                match_mode:
                                  structuredDSL.match_mode,
                              },

                              refinedInstruction:
                                null,

                              entityName:
                                null,

                              tags: [
                                'structured',
                              ],

                              priority: 50,
                            }
                          )

                          setStructuredName('')
                          setStructuredDSL(null)
                        } catch {
                          // handlePolicyCreate already
                          // stores the error message.
                        } finally {
                          setIsSavingStructured(
                            false
                          )
                        }
                      }}
                    >
                      {isSavingStructured ||
                      isCreatingPolicy ? (
                        <>
                          <Icons.loader className="mr-2 h-4 w-4 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <Icons.check className="mr-2 h-4 w-4" />
                          Save Policy
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* ================================================================ */}
        {/* PERMISSION MATRIX */}
        {/* ================================================================ */}

        {activeTab === 'matrix' && (
          <motion.div
            key="matrix-tab"
            initial={{
              opacity: 0,
              x: 20,
            }}
            animate={{
              opacity: 1,
              x: 0,
            }}
            exit={{
              opacity: 0,
              x: -20,
            }}
            transition={{
              duration: 0.15,
            }}
          >
            <PermissionMatrixTab />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ================================================================== */}
      {/* Detail Modal */}
      {/* ================================================================== */}

      <PolicyDetailModal
        policy={selectedPolicy}
        isOpen={isDetailModalOpen}
        onClose={() => {
          setIsDetailModalOpen(false)
          setSelectedPolicy(null)
        }}
        onEdit={handleEditFromDetail}
        onToggleStatus={(
          id,
          isActive
        ) => {
          togglePolicyStatus(
            id,
            isActive
          )

          setIsDetailModalOpen(false)
          setSelectedPolicy(null)
        }}
        onDelete={(id) => {
          deletePolicy(id)

          setIsDetailModalOpen(false)
          setSelectedPolicy(null)
        }}
      />

      {/* ================================================================== */}
      {/* Edit Modal */}
      {/* ================================================================== */}

      <PolicyEditModal
        policy={editingPolicy}
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false)
          setEditingPolicy(null)
        }}
        onSave={handleSavePolicy}
      />
    </motion.div>
  )
}

