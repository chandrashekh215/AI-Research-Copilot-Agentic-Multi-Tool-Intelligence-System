import { useEffect, useRef } from 'react'
import type { AgentStep, JobStatus } from '../api/client'

interface Props {
  steps: AgentStep[]
  status: JobStatus
  stepsCompleted: number
  latestAction: string | null
  topic: string
  depthMax: number
}

const ACTION_ICONS: Record<string, string> = {
  web_search:       '🌐',
  read_url:         '📄',
  arxiv_search:     '📚',
  wikipedia_search: '🔎',
  synthesize_report:'✍️',
}

const ACTION_LABELS: Record<string, string> = {
  web_search:       'Web Search',
  read_url:         'Reading URL',
  arxiv_search:     'ArXiv Search',
  wikipedia_search: 'Wikipedia',
  synthesize_report:'Synthesizing Report',
}

function StatusBadge({ status }: { status: JobStatus }) {
  const labels: Record<JobStatus, string> = {
    pending: 'Pending', running: 'Researching', completed: 'Complete', failed: 'Failed'
  }
  return (
    <span className={`status-badge status-${status}`}>
      {status === 'running' && <span className="pulse" />}
      {labels[status]}
    </span>
  )
}

export default function AgentTrace({ steps, status, stepsCompleted, latestAction, topic, depthMax }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [steps.length])

  const progressPct = status === 'completed'
    ? 100
    : Math.min(Math.round((stepsCompleted / depthMax) * 85), 85)

  return (
    <div className="card">
      <div className="card-title" style={{ justifyContent: 'space-between' }}>
        <span>🤖 Agent Reasoning Trace</span>
        <StatusBadge status={status} />
      </div>

      {(status === 'running' || status === 'completed') && (
        <div className="progress-bar-wrap">
          <div className="progress-bar-fill" style={{ width: `${progressPct}%` }} />
        </div>
      )}

      {topic && (
        <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
          Researching: <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>"{topic}"</span>
          &nbsp;·&nbsp;{stepsCompleted} step{stepsCompleted !== 1 ? 's' : ''} completed
          {latestAction && status === 'running' && (
            <>&nbsp;·&nbsp;Now: <span style={{ color: 'var(--text-link)' }}>{ACTION_LABELS[latestAction] ?? latestAction}</span></>
          )}
        </div>
      )}

      <div className="trace-container">
        {steps.length === 0 ? (
          <div className="trace-empty">
            {status === 'pending'
              ? '⏳ Agent is initialising...'
              : 'No steps recorded yet.'}
          </div>
        ) : (
          steps.map((step, i) => {
            const isLast = i === steps.length - 1
            const isDone = status === 'completed' || !isLast
            const icon   = ACTION_ICONS[step.action] ?? '⚙️'
            const label  = ACTION_LABELS[step.action] ?? step.action

            return (
              <div
                key={step.step_number}
                className={`trace-step ${isLast && status === 'running' ? 'active' : isDone ? 'done' : ''}`}
              >
                <div className="step-number">{step.step_number}</div>
                <div className="step-content">
                  <div className="step-action">{icon} {label}</div>
                  <div className="step-input">{step.input}</div>
                  {step.output && step.output !== '⏳ running...' && (
                    <div className="step-output">{step.output}</div>
                  )}
                  {step.output === '⏳ running...' && (
                    <div className="step-output" style={{ color: 'var(--text-link)' }}>
                      <span className="pulse" style={{ display: 'inline-block', marginRight: 6 }} />
                      Running...
                    </div>
                  )}
                </div>
              </div>
            )
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
