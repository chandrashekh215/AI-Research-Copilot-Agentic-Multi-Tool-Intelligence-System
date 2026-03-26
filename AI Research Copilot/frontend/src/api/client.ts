import axios from 'axios'

const api = axios.create({ baseURL: '' })

// ── Types ─────────────────────────────────────────────────────────────────────

export type Depth = 'quick' | 'normal' | 'deep'
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface ResearchRequest {
  topic: string
  depth: Depth
  include_arxiv: boolean
}

export interface AgentStep {
  step_number: number
  action: string
  input: string
  output: string
  timestamp: string
}

export interface Source {
  title: string
  url: string | null
  source_type: 'web' | 'arxiv' | 'wikipedia'
  snippet: string
}

export interface Report {
  id: string
  topic: string
  depth: Depth
  executive_summary: string
  key_findings: string[]
  detailed_analysis: string
  follow_up_questions: string[]
  sources: Source[]
  full_markdown: string
  created_at: string
}

export interface StatusResponse {
  job_id: string
  topic: string
  status: JobStatus
  steps_completed: number
  latest_action: string | null
  error: string | null
}

export interface StepsResponse {
  job_id: string
  steps: AgentStep[]
}

export interface ReportListItem {
  job_id: string
  topic: string
  depth: Depth
  status: JobStatus
  sources_count: number
  created_at: string
}

// ── API Calls ─────────────────────────────────────────────────────────────────

export const startResearch = async (req: ResearchRequest) => {
  const res = await api.post<{ job_id: string; message: string; status: JobStatus }>('/research', req)
  return res.data
}

export const getStatus = async (jobId: string): Promise<StatusResponse> => {
  const res = await api.get<StatusResponse>(`/status/${jobId}`)
  return res.data
}

export const getSteps = async (jobId: string): Promise<StepsResponse> => {
  const res = await api.get<StepsResponse>(`/steps/${jobId}`)
  return res.data
}

export const getReport = async (jobId: string): Promise<Report> => {
  const res = await api.get<Report>(`/report/${jobId}`)
  return res.data
}

export const listReports = async (): Promise<ReportListItem[]> => {
  const res = await api.get<{ total: number; reports: ReportListItem[] }>('/reports')
  return res.data.reports
}

export const deleteReport = async (jobId: string) => {
  await api.delete(`/report/${jobId}`)
}
