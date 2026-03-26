import { useEffect, useState } from 'react'
import { listReports, deleteReport, type ReportListItem, type JobStatus } from '../api/client'

interface Props {
  onSelectJob: (jobId: string, topic: string) => void
  refreshTick: number
}

function StatusBadge({ status }: { status: JobStatus }) {
  const map: Record<JobStatus, { label: string; cls: string }> = {
    pending:   { label: 'Pending',     cls: 'status-pending' },
    running:   { label: 'Running',     cls: 'status-running' },
    completed: { label: 'Completed',   cls: 'status-completed' },
    failed:    { label: 'Failed',      cls: 'status-failed' },
  }
  const { label, cls } = map[status]
  return <span className={`status-badge ${cls}`}>{label}</span>
}

export default function ReportHistory({ onSelectJob, refreshTick }: Props) {
  const [reports, setReports] = useState<ReportListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  const load = async () => {
    try {
      setError('')
      const data = await listReports()
      setReports(data)
    } catch {
      setError('Could not load reports. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [refreshTick])

  const handleDelete = async (e: React.MouseEvent, jobId: string) => {
    e.stopPropagation()
    if (!confirm('Delete this report?')) return
    try {
      await deleteReport(jobId)
      setReports(prev => prev.filter(r => r.job_id !== jobId))
    } catch {
      alert('Failed to delete report.')
    }
  }

  if (loading) {
    return (
      <div className="card">
        <div className="card-title">📁 Report History</div>
        <div className="trace-empty">Loading reports...</div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-title" style={{ justifyContent: 'space-between' }}>
        <span>📁 Report History</span>
        <button className="copy-btn" onClick={load}>↻ Refresh</button>
      </div>

      {error && <div className="error-box" style={{ marginBottom: 16 }}>{error}</div>}

      {reports.length === 0 ? (
        <div className="empty-state">
          <div className="big-icon">🗂️</div>
          <p>No reports yet. Start your first research job!</p>
        </div>
      ) : (
        <div className="history-list">
          {reports.map(r => (
            <div
              key={r.job_id}
              className="history-item"
              onClick={() => r.status === 'completed' && onSelectJob(r.job_id, r.topic)}
            >
              <div style={{ flex: '0 0 auto' }}>
                <StatusBadge status={r.status} />
              </div>

              <div className="history-topic" title={r.topic}>{r.topic}</div>

              <div className="history-meta">
                <span>{r.sources_count} source{r.sources_count !== 1 ? 's' : ''}</span>
                <span className="tag">{r.depth}</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {new Date(r.created_at).toLocaleString()}
                </span>
              </div>

              <button
                className="copy-btn"
                style={{ flexShrink: 0 }}
                onClick={(e) => handleDelete(e, r.job_id)}
                title="Delete"
              >
                🗑️
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
