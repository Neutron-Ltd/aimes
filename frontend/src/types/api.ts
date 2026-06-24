/** Health check response from GET /api/v1/health */
export interface HealthResponse {
  status?: string
  [key: string]: unknown
}

/** Text query request payload for POST /api/v1/query */
export interface QueryRequest {
  query: string
  enrich_response: boolean
}

/** Standard query response from POST /api/v1/query and /api/v1/query/voice */
export interface QueryResponse {
  intent: string | Record<string, unknown>
  tool_name: string | null
  result: QueryResultPayload | null
  message: string
  metadata: Record<string, unknown>
  transcript?: string | null
}

/** Structured MCP tool output — drives charts and debug accordion */
export interface QueryResultPayload {
  value?: number
  defect_rate?: number
  metric?: string
  breakdown?: BreakdownRow[]
  [key: string]: unknown
}

/** Single row inside result.breakdown time-series or category arrays */
export interface BreakdownRow {
  bucket?: string | null
  date?: string | null
  value?: number
  defect_rate?: number
  process_code?: string
  inspected?: number
  defects?: number
  [key: string]: unknown
}

/** Chat message displayed in the UI */
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'error'
  content: string
  timestamp: Date
  /** Full API response wrapper for assistant messages */
  response?: QueryResponse
}

/** Event log entry when backend returns structured result data */
export interface EventLogEntry {
  id: string
  timestamp: Date
  intent: string
  toolName: string
  schemaTables: string[]
  resultPreview: string
}

/** Shared app configuration */
export interface AppConfig {
  baseURL: string
  workshopId: string
  enrichResponse: boolean
}

/** Health status for dashboard indicator */
export type HealthStatus = 'healthy' | 'unhealthy' | 'checking'

/** Quick-click chip definition */
export interface QuickChip {
  id: string
  label: string
  query: string
}

export const QUICK_CHIPS: QuickChip[] = [
  {
    id: 'chip-a',
    label: 'Line FDQ-SMT-3 Yield',
    query: 'Total equipment yield on line FDQ-SMT-3 for 2026-06-20',
  },
  {
    id: 'chip-b',
    label: 'Device BB-SMT-029 Yield',
    query: 'Equipment yield for device BB-SMT-029 on 2026-06-20',
  },
  {
    id: 'chip-c',
    label: 'Cross-Module FDQ-SMT-3',
    query: 'Cross-module analysis for line FDQ-SMT-3',
  },
  {
    id: 'chip-d',
    label: 'Obsolete Inventory 90d',
    query: 'Profile obsolete inventory older than 90 days',
  },
]
