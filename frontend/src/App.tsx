import { useState, useEffect, useRef, useCallback } from 'react'
import ResearchForm from './components/ResearchForm'
import AgentTrace from './components/AgentTrace'
import ReportViewer from './components/ReportViewer'
import ReportHistory from './components/ReportHistory'
import { getStatus, getSteps, getReport, type AgentStep, type JobStatus, type Report, type Depth } from './api/client'

type View = 'home' | 'history'

const DEPTH_MAX: Record<Depth, number> = { quick: 6, normal: 12, deep: 20 }

interface ActiveJob {
  jobId: string
  topic: string
  depth: Depth
  status: JobStatus
  steps: AgentStep[]
  stepsCompleted: number
  latestAction: string | null
  report: Report | null
  error: string | null
}

export default function App() {
  const [view, setView]             = useState<View>('home')
  const [activeJob, setActiveJob]   = useState<ActiveJob | null>(null)
  const [historyTick, setHistoryTick] = useState(0)

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── Stop polling ──────────────────────────────────────────────────────────
  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }, [])

  // ── Start polling ─────────────────────────────────────────────────────────
  const startPolling = useCallback((jobId: string) => {
    stopPolling()

    pollingRef.current = setInterval(async () => {
      try {
        const [statusData, stepsData] = await Promise.all([
          getStatus(jobId),
          getSteps(jobId),
        ])

        setActiveJob(prev => prev
          ? {
              ...prev,
              status: statusData.status,
              stepsCompleted: statusData.steps_completed,
              latestAction: statusData.latest_action,
              steps: stepsData.steps,
              error: statusData.error,
            }
          : prev
        )

        // Job finished — fetch report
        if (statusData.status === 'completed') {
          stopPolling()
          const report = await getReport(jobId)
          setActiveJob(prev => prev ? { ...prev, report } : prev)
          setHistoryTick(t => t + 1)
        }

        if (statusData.status === 'failed') {
          stopPolling()
          setHistoryTick(t => t + 1)
        }

      } catch (err) {
        console.error('Polling error:', err)
      }
    }, 2000)
  }, [stopPolling])

  // ── Cleanup on unmount ────────────────────────────────────────────────────
  useEffect(() => () => stopPolling(), [stopPolling])

  // ── New job started ───────────────────────────────────────────────────────
  const handleJobStarted = (jobId: string, topic: string) => {
    // Try to infer depth from active form state — default normal
    const job: ActiveJob = {
      jobId, topic,
      depth: 'normal',
      status: 'pending',
      steps: [],
      stepsCompleted: 0,
      latestAction: null,
      report: null,
      error: null,
    }
    setActiveJob(job)
    setView('home')
    startPolling(jobId)
  }

  // ── Load a completed job from history ─────────────────────────────────────
  const handleSelectFromHistory = async (jobId: string, topic: string) => {
    try {
      const [statusData, stepsData, report] = await Promise.all([
        getStatus(jobId),
        getSteps(jobId),
        getReport(jobId),
      ])
      setActiveJob({
        jobId, topic,
        depth: 'normal',
        status: statusData.status,
        steps: stepsData.steps,
        stepsCompleted: statusData.steps_completed,
        latestAction: null,
        report,
        error: null,
      })
      setView('home')
    } catch (err) {
      console.error('Failed to load job:', err)
    }
  }

  const isRunning = activeJob?.status === 'running' || activeJob?.status === 'pending'

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="header-logo">
          🔬 Research<span className="dot">Agent</span>
        </div>
        <nav className="header-nav">
          <button className={`nav-btn ${view === 'home' ? 'active' : ''}`} onClick={() => setView('home')}>
            🏠 Home
          </button>
          <button className={`nav-btn ${view === 'history' ? 'active' : ''}`} onClick={() => { setView('history'); setHistoryTick(t => t + 1) }}>
            📁 History
          </button>
        </nav>
      </header>

      {/* ── Main ── */}
      <main className="main">
        {view === 'home' && (
          <>
            <ResearchForm onJobStarted={handleJobStarted} isRunning={!!isRunning} />

            {activeJob && (
              <>
                <hr className="divider" />

                {activeJob.error && (
                  <div className="error-box" style={{ marginBottom: 24 }}>
                    ❌ Research failed: {activeJob.error}
                  </div>
                )}

                <AgentTrace
                  steps={activeJob.steps}
                  status={activeJob.status}
                  stepsCompleted={activeJob.stepsCompleted}
                  latestAction={activeJob.latestAction}
                  topic={activeJob.topic}
                  depthMax={DEPTH_MAX[activeJob.depth]}
                />

                {activeJob.report && (
                  <ReportViewer report={activeJob.report} />
                )}
              </>
            )}

            {!activeJob && (
              <div className="empty-state" style={{ marginTop: 40 }}>
                <div className="big-icon">🤖</div>
                <p>Enter a topic above and click <strong>Start Research</strong></p>
                <p style={{ marginTop: 8, fontSize: 13 }}>
                  The agent will autonomously search the web, read articles, scan academic papers, and write a full report.
                </p>
              </div>
            )}
          </>
        )}

        {view === 'history' && (
          <ReportHistory onSelectJob={handleSelectFromHistory} refreshTick={historyTick} />
        )}
      </main>
    </div>
  )
}
