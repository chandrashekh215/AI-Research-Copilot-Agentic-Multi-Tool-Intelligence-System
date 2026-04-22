import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Report } from '../api/client'

interface Props {
  report: Report
}

type Tab = 'structured' | 'markdown'

const SOURCE_BADGE: Record<string, string> = {
  web: 'badge-web', arxiv: 'badge-arxiv', wikipedia: 'badge-wikipedia'
}

export default function ReportViewer({ report }: Props) {
  const [tab, setTab]       = useState<Tab>('structured')
  const [copied, setCopied] = useState(false)

  const copyMarkdown = async () => {
    await navigator.clipboard.writeText(report.full_markdown)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="card">
      <div className="card-title" style={{ justifyContent: 'space-between' }}>
        <span>📋 Research Report</span>
        <button className="copy-btn" onClick={copyMarkdown}>
          {copied ? '✓ Copied!' : '📋 Copy Markdown'}
        </button>
      </div>

      {/* Topic + meta row */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 6 }}>{report.topic}</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <span className="tag">Depth: {report.depth}</span>
          <span className="tag">{report.sources.length} sources</span>
          <span className="tag">{report.key_findings.length} key findings</span>
          <span className="tag" style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>
            {new Date(report.created_at).toLocaleString()}
          </span>
        </div>
      </div>

      {/* Tab switcher */}
      <div className="report-tabs">
        <button className={`report-tab ${tab === 'structured' ? 'active' : ''}`} onClick={() => setTab('structured')}>
          Structured View
        </button>
        <button className={`report-tab ${tab === 'markdown' ? 'active' : ''}`} onClick={() => setTab('markdown')}>
          Markdown
        </button>
      </div>

      {tab === 'structured' ? (
        <>
          {/* Executive Summary */}
          <div className="report-section">
            <h2>Executive Summary</h2>
            <p style={{ fontSize: 14, lineHeight: 1.8 }}>{report.executive_summary}</p>
          </div>

          {/* Key Findings */}
          <div className="report-section">
            <h2>Key Findings</h2>
            <ul className="findings-list">
              {report.key_findings.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          </div>

          {/* Detailed Analysis */}
          <div className="report-section">
            <h2>Detailed Analysis</h2>
            <p className="analysis-text">{report.detailed_analysis}</p>
          </div>

          {/* Follow-up Questions */}
          {report.follow_up_questions.length > 0 && (
            <div className="report-section">
              <h2>Follow-up Questions</h2>
              <div className="fq-list">
                {report.follow_up_questions.map((q, i) => (
                  <div key={i} className="fq-item">💡 {q}</div>
                ))}
              </div>
            </div>
          )}

          {/* Sources */}
          {report.sources.length > 0 && (
            <div className="report-section">
              <h2>Sources ({report.sources.length})</h2>
              <div className="sources-grid">
                {report.sources.map((s, i) => (
                  <div key={i} className="source-item">
                    <span className={`source-badge ${SOURCE_BADGE[s.source_type] ?? ''}`}>
                      {s.source_type}
                    </span>
                    <span className="source-title">{s.title}</span>
                    {s.url && (
                      <a className="source-link" href={s.url} target="_blank" rel="noreferrer">
                        ↗ open
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="markdown-view">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {report.full_markdown}
          </ReactMarkdown>
        </div>
      )}
    </div>
  )
}
