import { useState } from 'react'
import { startResearch, type Depth, type ResearchRequest } from '../api/client'

interface Props {
  onJobStarted: (jobId: string, topic: string) => void
  isRunning: boolean
}

const DEPTH_OPTIONS: { value: Depth; label: string; desc: string; time: string }[] = [
  { value: 'quick',  label: '⚡ Quick',  desc: '2–3 sources', time: '~1 min' },
  { value: 'normal', label: '🔍 Normal', desc: '5–7 sources', time: '~3 min' },
  { value: 'deep',   label: '🧠 Deep',   desc: '10+ sources', time: '~7 min' },
]

export default function ResearchForm({ onJobStarted, isRunning }: Props) {
  const [topic, setTopic]               = useState('')
  const [depth, setDepth]               = useState<Depth>('normal')
  const [includeArxiv, setIncludeArxiv] = useState(true)
  const [error, setError]               = useState('')
  const [loading, setLoading]           = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!topic.trim() || topic.trim().length < 5) {
      setError('Please enter a topic with at least 5 characters.')
      return
    }

    setError('')
    setLoading(true)

    try {
      const req: ResearchRequest = { topic: topic.trim(), depth, include_arxiv: includeArxiv }
      const res = await startResearch(req)
      onJobStarted(res.job_id, topic.trim())
      setTopic('')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to start research. Is the backend running?'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <div className="card-title">
        🔬 Research Topic
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">What do you want to research?</label>
          <textarea
            className="form-input"
            rows={3}
            placeholder="e.g. Impact of AI on Healthcare in 2025, Quantum computing breakthroughs..."
            value={topic}
            onChange={e => setTopic(e.target.value)}
            disabled={isRunning || loading}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Research Depth</label>
          <div className="depth-selector">
            {DEPTH_OPTIONS.map(opt => (
              <div
                key={opt.value}
                className={`depth-option ${depth === opt.value ? 'selected' : ''}`}
                onClick={() => !isRunning && setDepth(opt.value)}
              >
                <strong>{opt.label}</strong>
                {opt.desc}
                <br />
                <span style={{ fontSize: 11, opacity: 0.7 }}>{opt.time}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={includeArxiv}
              onChange={e => setIncludeArxiv(e.target.checked)}
              disabled={isRunning || loading}
            />
            Include academic papers from ArXiv
          </label>
        </div>

        {error && <div className="error-box" style={{ marginBottom: 16 }}>{error}</div>}

        <button
          type="submit"
          className="submit-btn"
          disabled={isRunning || loading || !topic.trim()}
        >
          {loading ? (
            <>
              <span className="pulse" style={{ background: '#fff' }} />
              Starting...
            </>
          ) : isRunning ? (
            <>⏳ Research in progress...</>
          ) : (
            <>🚀 Start Research</>
          )}
        </button>
      </form>
    </div>
  )
}
