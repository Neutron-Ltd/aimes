/** Chart point extracted from MCP tool result.breakdown rows */
export interface ChartPoint {
  label: string
  value: number
}

export interface ChartPayload {
  points: ChartPoint[]
  yAxisLabel: string
  chartType: 'line' | 'bar'
  title?: string
}

const X_AXIS_KEYS = ['bucket', 'date', 'period', 'hour', 'process_code', 'item_name', 'line_id', 'device_sn']
const Y_AXIS_KEYS = ['value', 'defect_rate', 'rate', 'qty', 'quantity', 'achievement_rate', 'throughput', 'yield']

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

/** Resolve the primary scalar metric on a result object (value, defect_rate, etc.). */
export function getMainMetricValue(result: Record<string, unknown>): number | null {
  for (const key of ['value', 'defect_rate', 'rate', 'total_defects', 'total_inspected']) {
    const v = result[key]
    if (typeof v === 'number' && Number.isFinite(v)) return v
  }
  return null
}

function formatBucketLabel(raw: unknown): string {
  if (raw == null) return '—'
  const str = String(raw)
  // Shorten ISO timestamps for axis readability
  if (/^\d{4}-\d{2}-\d{2}T/.test(str)) {
    const d = new Date(str)
    if (!Number.isNaN(d.getTime())) {
      return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      })
    }
  }
  return str
}

function resolveXKey(row: Record<string, unknown>): string | null {
  for (const key of X_AXIS_KEYS) {
    if (key in row && row[key] != null) return key
  }
  const fallback = Object.keys(row).find(
    (k) => typeof row[k] === 'string' && !Y_AXIS_KEYS.includes(k),
  )
  return fallback ?? null
}

function resolveYKey(row: Record<string, unknown>): string | null {
  for (const key of Y_AXIS_KEYS) {
    if (key in row && typeof row[key] === 'number') return key
  }
  const fallback = Object.keys(row).find(
    (k) => typeof row[k] === 'number' && k !== 'inspected' && k !== 'defects',
  )
  return fallback ?? null
}

function looksLikeTimeSeries(labels: string[]): boolean {
  return labels.some((l) => /^\d{4}-\d{2}-\d{2}/.test(l) || /\d{1,2}:\d{2}/.test(l))
}

function extractBreakdownPoints(breakdown: unknown[]): ChartPoint[] {
  const points: ChartPoint[] = []

  for (const item of breakdown) {
    if (!isRecord(item)) continue
    const xKey = resolveXKey(item)
    const yKey = resolveYKey(item)
    if (!xKey || !yKey) continue

    const rawValue = item[yKey]
    if (typeof rawValue !== 'number' || !Number.isFinite(rawValue)) continue

    points.push({
      label: formatBucketLabel(item[xKey]),
      value: rawValue,
    })
  }

  return points
}

/**
 * Decide whether the chart canvas should render for a given result payload.
 * Hidden when result is null/empty or the primary metric is exactly zero.
 */
export function shouldShowChart(result: unknown): boolean {
  if (!isRecord(result)) return false

  const main = getMainMetricValue(result)
  if (main === 0) return false

  const breakdown = result.breakdown
  if (Array.isArray(breakdown) && breakdown.length > 0) {
    const points = extractBreakdownPoints(breakdown)
    if (points.length > 0 && points.some((p) => p.value !== 0)) return true
  }

  return main !== null && main !== 0
}

/** Build ECharts-ready series data from a structured MCP result object. */
export function buildChartPayload(result: unknown): ChartPayload | null {
  if (!shouldShowChart(result) || !isRecord(result)) return null

  const breakdown = result.breakdown
  if (Array.isArray(breakdown) && breakdown.length > 0) {
    const points = extractBreakdownPoints(breakdown)
    if (points.length === 0) return null

    const sample = breakdown.find(isRecord)
    const yKey = sample ? resolveYKey(sample) : 'value'
    const labels = points.map((p) => p.label)

    return {
      points,
      yAxisLabel: yKey ?? 'value',
      chartType: looksLikeTimeSeries(labels) ? 'line' : 'bar',
      title: typeof result.metric === 'string' ? result.metric : undefined,
    }
  }

  const main = getMainMetricValue(result)
  if (main === null || main === 0) return null

  return {
    points: [{ label: 'Total', value: main }],
    yAxisLabel: 'value',
    chartType: 'bar',
    title: typeof result.metric === 'string' ? result.metric : 'Metric',
  }
}
