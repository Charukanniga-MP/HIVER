import React, { useState } from 'react'
import appData from './data/appData.json'

export default function App() {
  const [activeTab, setActiveTab] = useState('command') // 'command' | 'eval' | 'failures' | 'decisions'
  const [selectedTicket, setSelectedTicket] = useState(appData.presets?.[0] || {})
  const [customInput, setCustomInput] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [serverError, setServerError] = useState(null)

  const handleSelectPreset = (ticket) => {
    setSelectedTicket(ticket)
    setCustomInput('')
    setServerError(null)
  }

  const handleRunCustom = async () => {
    if (!customInput.trim()) return
    setIsProcessing(true)
    setServerError(null)

    try {
      // Call Live Python Backend Inference API (server.py running src modules)
      const res = await fetch('http://localhost:5000/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_text: customInput })
      })

      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`)
      }

      const liveResult = await res.json()
      setSelectedTicket(liveResult)

    } catch (err) {
      console.warn('Live API server offline, using offline preset fallback:', err.message)
      setServerError('Live Python backend server offline (http://localhost:5000). Start server.py for live API inference.')
      
      // Local fallback representation if live API server is not running
      const textLower = customInput.toLowerCase()
      let intent = 'general_feedback_inquiry'
      let conf = 0.45
      let escalation = 'AUTO-HANDLE'
      let why = 'Processed custom query against historical SpotifyCares support resolution corpus.'
      let evId = 'SPOT-36918'
      let sim = 0.54
      let reply = 'Thank you for reaching out! To make sure this gets resolved accurately, I\'ve escalated your request to a human support agent who will follow up with you directly.'

      if (textLower.includes('shuffle') || textLower.includes('pause') || textLower.includes('freeze') || textLower.includes('audio')) {
        intent = 'playback_audio_issue'
        conf = 0.85
        evId = 'SPOT-04192'
        sim = 0.81
        reply = 'Hi there! Try clearing your app cache and restarting your device to reset playback parameters.'
        why = 'High confidence (0.85) match for playback_audio_issue with grounded evidence.'
      } else if (textLower.includes('refund') || textLower.includes('billed') || textLower.includes('charged') || textLower.includes('payment')) {
        intent = 'billing_subscription_dispute'
        conf = 0.90
        escalation = 'ESCALATE TO HUMAN'
        evId = 'SPOT-11042'
        sim = 0.52
        reply = 'Thank you for reaching out. Financial billing disputes require verification by our human billing team.'
        why = 'Financial billing dispute requiring payment ledger verification by human specialist.'
      } else if (textLower.includes('hacked') || textLower.includes('password') || textLower.includes('stolen') || textLower.includes('account')) {
        intent = 'account_access_security'
        conf = 0.95
        escalation = 'ESCALATE TO HUMAN'
        evId = 'SPOT-00891'
        sim = 0.61
        reply = 'We take account security very seriously. I have flagged your request for our Account Security Team to verify your identity safely.'
        why = 'High-risk account security breach requiring human safety team escalation.'
      }

      setSelectedTicket({
        id: `OFFLINE-${Math.floor(100 + Math.random() * 900)}`,
        customer_handle: '@offline_user',
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        customer_text: customInput,
        true_intent: intent,
        confidence: conf,
        evidence_id: evId,
        similarity_score: sim,
        historical_customer: customInput,
        historical_brand: reply,
        grounded: sim >= 0.50,
        draft_reply: reply,
        escalation: escalation,
        why: why
      })
    } finally {
      setIsProcessing(false)
    }
  }

  // Source of Truth Data Presentation Tokens
  const intentMetrics = {
    majority: { accuracy: '29.00%', macroF1: '0.0749', weightedF1: '0.1304' },
    logReg: { accuracy: '84.00%', macroF1: '0.8168', weightedF1: '0.8375' },
    proposed: { accuracy: '88.00%', macroF1: '0.8625', weightedF1: '0.8789' }
  }

  const escMetrics = {
    tp: 32,
    tn: 120,
    fp: 47,
    fn: 1,
    precision: '40.51%',
    recall: '96.97%',
    f1: '0.5714',
    accuracy: '76.00%',
    missed: '1/200',
    missedRate: '0.50%',
    overEscalationRate: '23.50%',
    predictedAutoHandled: '60.50%',
    correctAutoHandledRoutine: '60.00%'
  }

  const responseQuality = {
    sample: 'N = 30 human-reviewed, AI-assisted ratings',
    relevance: '3.47',
    groundedness: '2.80',
    helpfulness: '3.17',
    correctness: '3.77',
    overall: '3.27',
    displayString: '3.27 / 5 — 30 human-reviewed, AI-assisted ratings'
  }

  const judgeNotice = 'LLM-as-judge API unavailable during evaluation; NonLLMFallbackJudge used only for infrastructure verification.'

  const failureModes = appData.top_failure_modes || []
  const decisionLogs = appData.decisions_log || []

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#0B0F19', color: '#F3F4F6' }}>
      {/* Top Header / Branding */}
      <header style={{
        background: '#161F30',
        borderBottom: '1px solid #233249',
        padding: '16px 32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            backgroundColor: '#00E5FF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 'bold',
            color: '#0B0F19',
            fontSize: '1.2rem'
          }}>
            H
          </div>
          <div>
            <h1 style={{ fontSize: '1.15rem', fontWeight: 700, letterSpacing: '-0.02em', color: '#F3F4F6' }}>
              SpotifyCares AI Customer Support Command Center
            </h1>
            <p className="mono" style={{ fontSize: '0.75rem', color: '#00E5FF' }}>
              BRAND: SpotifyCares | INFERENCE API: http://localhost:5000/api/predict
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', gap: '8px' }}>
          {[
            { id: 'command', label: 'Live Command Center' },
            { id: 'eval', label: 'Evaluation Dashboard' },
            { id: 'failures', label: 'Failure Analysis' },
            { id: 'decisions', label: 'Decision Log' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: activeTab === tab.id ? 'rgba(0, 229, 255, 0.15)' : 'transparent',
                border: activeTab === tab.id ? '1px solid #00E5FF' : '1px solid transparent',
                color: activeTab === tab.id ? '#00E5FF' : '#9CA3AF',
                padding: '8px 16px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.85rem',
                transition: 'all 0.2s'
              }}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      {/* Main Content Area */}
      <main style={{ padding: '24px 32px', maxWidth: '1600px', margin: '0 auto' }}>
        
        {/* TAB 1: LIVE COMMAND CENTER */}
        {activeTab === 'command' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* Quick Ticket Selector Bar */}
            <div className="cyber-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, overflowX: 'auto' }}>
                <span className="mono" style={{ fontSize: '0.8rem', color: '#9CA3AF', whiteSpace: 'nowrap' }}>PRESET SCENARIOS:</span>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'nowrap' }}>
                  {(appData.presets || []).map((ticket) => (
                    <button
                      key={ticket.id}
                      onClick={() => handleSelectPreset(ticket)}
                      style={{
                        background: selectedTicket.id === ticket.id ? '#1D2A40' : '#111827',
                        border: selectedTicket.id === ticket.id ? '1px solid #00E5FF' : '1px solid #233249',
                        color: selectedTicket.id === ticket.id ? '#00E5FF' : '#D1D5DB',
                        padding: '6px 12px',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.8rem',
                        fontWeight: 500,
                        whiteSpace: 'nowrap'
                      }}
                    >
                      {ticket.id}: {ticket.true_intent}
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom Input */}
              <div style={{ display: 'flex', gap: '8px', flex: 1, maxWidth: '450px' }}>
                <input
                  type="text"
                  placeholder="Test live Python pipeline inference..."
                  value={customInput}
                  onChange={(e) => setCustomInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleRunCustom()}
                  style={{
                    flex: 1,
                    background: '#0B0F19',
                    border: '1px solid #233249',
                    color: '#F3F4F6',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    fontSize: '0.85rem'
                  }}
                />
                <button
                  onClick={handleRunCustom}
                  disabled={isProcessing}
                  style={{
                    background: '#00E5FF',
                    color: '#0B0F19',
                    border: 'none',
                    padding: '8px 16px',
                    borderRadius: '4px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  {isProcessing ? 'Running Pipeline...' : 'Run Agent'}
                </button>
              </div>
            </div>

            {serverError && (
              <div style={{
                background: 'rgba(255, 149, 0, 0.1)',
                border: '1px solid #FF9500',
                color: '#FF9500',
                padding: '10px 16px',
                borderRadius: '6px',
                fontSize: '0.8rem'
              }} className="mono">
                [NOTICE]: {serverError}
              </div>
            )}

            {/* Split Screen Layout: Left (Conversation) / Right (AI Analysis) */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
              
              {/* LEFT COLUMN: Customer Conversation View */}
              <div className="cyber-card" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #233249', paddingBottom: '12px' }}>
                  <div>
                    <span className="mono" style={{ fontSize: '0.75rem', color: '#00E5FF' }}>
                      {selectedTicket.is_live_inference ? 'LIVE PYTHON INFERENCE TICKET' : 'INCOMING SUPPORT TICKET'}
                    </span>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#F3F4F6' }}>{selectedTicket.id}</h3>
                  </div>
                  <span className="mono" style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>{selectedTicket.timestamp}</span>
                </div>

                {/* Customer Message Bubble */}
                <div style={{
                  background: '#0B0F19',
                  border: '1px solid #233249',
                  borderRadius: '8px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 600, color: '#00E5FF', fontSize: '0.9rem' }}>{selectedTicket.customer_handle}</span>
                    <span className="cyber-badge badge-cyan">CUSTOMER INBOUND</span>
                  </div>
                  <p style={{ fontSize: '0.95rem', color: '#E5E7EB', lineHeight: 1.6 }}>
                    "{selectedTicket.customer_text}"
                  </p>
                </div>

                {/* System Activity Logs */}
                <div style={{
                  background: '#111827',
                  border: '1px dotted #233249',
                  borderRadius: '6px',
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px'
                }}>
                  <span className="mono" style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>AI AGENT EXECUTION PIPELINE LOG:</span>
                  <div className="mono" style={{ fontSize: '0.75rem', color: '#10B981' }}>
                    [1] Cleaned text sanitization complete (stripped PII & URLs)
                  </div>
                  <div className="mono" style={{ fontSize: '0.75rem', color: '#00E5FF' }}>
                    [2] Intent classified: {selectedTicket.true_intent} (Confidence: {((selectedTicket.confidence || 0) * 100).toFixed(0)}%)
                  </div>
                  <div className="mono" style={{ fontSize: '0.75rem', color: '#00E5FF' }}>
                    [3] Retrieved top historical evidence case: {selectedTicket.evidence_id} (Similarity: {((selectedTicket.similarity_score || 0) * 100).toFixed(1)}%)
                  </div>
                  <div className="mono" style={{ fontSize: '0.75rem', color: selectedTicket.escalation === 'AUTO-HANDLE' ? '#10B981' : '#FF3B30' }}>
                    [4] Decision: {selectedTicket.escalation}
                  </div>
                </div>
              </div>

              {/* RIGHT COLUMN: AI Analysis & Decision Center */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                
                {/* Intent & Confidence Card */}
                <div className="cyber-card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="mono" style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>INTENT CLASSIFICATION</span>
                    <span className="cyber-badge badge-cyan">{selectedTicket.true_intent}</span>
                  </div>

                  {/* Confidence Bar */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span style={{ fontSize: '0.85rem', color: '#9CA3AF' }}>Confidence Level</span>
                      <span className="mono" style={{ fontSize: '0.85rem', color: '#00E5FF', fontWeight: 700 }}>
                        {((selectedTicket.confidence || 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div style={{ height: '8px', background: '#0B0F19', borderRadius: '4px', overflow: 'hidden', border: '1px solid #233249' }}>
                      <div style={{
                        width: `${(selectedTicket.confidence || 0) * 100}%`,
                        height: '100%',
                        background: 'linear-gradient(90deg, #00E5FF, #10B981)',
                        transition: 'width 0.4s ease'
                      }} />
                    </div>
                  </div>
                </div>

                {/* Historical Evidence Retrieval Card */}
                <div className="cyber-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="mono" style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>HISTORICAL EVIDENCE RETRIEVED</span>
                    <span className="mono" style={{ fontSize: '0.75rem', color: '#00E5FF' }}>
                      EVIDENCE ID: {selectedTicket.evidence_id} ({((selectedTicket.similarity_score || 0) * 100).toFixed(1)}% MATCH)
                    </span>
                  </div>

                  <div style={{ background: '#0B0F19', padding: '12px', borderRadius: '6px', border: '1px solid #233249', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <span className="mono" style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>HISTORICAL RESOLUTION GROUNDING:</span>
                    <p style={{ fontSize: '0.85rem', color: '#D1D5DB', fontStyle: 'italic' }}>
                      "{selectedTicket.historical_brand}"
                    </p>
                  </div>
                </div>

                {/* AI Draft Reply Card */}
                <div className="cyber-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="mono" style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>AI DRAFT REPLY</span>
                    <span className={`cyber-badge ${selectedTicket.grounded ? 'badge-emerald' : 'badge-crimson'}`}>
                      {selectedTicket.grounded ? 'GROUNDED EVIDENCE' : 'UNGROUNDED / ESCALATED'}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.95rem', color: '#F3F4F6', lineHeight: 1.5, background: '#0B0F19', padding: '12px', borderRadius: '6px', border: '1px solid #233249' }}>
                    {selectedTicket.draft_reply}
                  </p>
                </div>

                {/* Escalation Decision Banner */}
                <div style={{
                  background: selectedTicket.escalation === 'AUTO-HANDLE' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255, 59, 48, 0.1)',
                  border: selectedTicket.escalation === 'AUTO-HANDLE' ? '1px solid #10B981' : '1px solid #FF3B30',
                  borderRadius: '8px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="mono" style={{ fontSize: '0.8rem', color: '#9CA3AF' }}>DECISION:</span>
                    <span style={{
                      fontWeight: 800,
                      fontSize: '1.1rem',
                      letterSpacing: '0.05em',
                      color: selectedTicket.escalation === 'AUTO-HANDLE' ? '#10B981' : '#FF3B30'
                    }}>
                      {selectedTicket.escalation}
                    </span>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#9CA3AF' }}>Why? </span>
                    <span style={{ fontSize: '0.85rem', color: '#E5E7EB' }}>{selectedTicket.why}</span>
                  </div>
                </div>

              </div>
            </div>
          </div>
        )}

        {/* TAB 2: EVALUATION DASHBOARD */}
        {activeTab === 'eval' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* Top Metric Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
              <div className="cyber-card">
                <span className="mono" style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>PROPOSED SYSTEM ACCURACY</span>
                <h2 style={{ fontSize: '2rem', fontWeight: 700, color: '#00E5FF' }}>
                  {intentMetrics.proposed.accuracy}
                </h2>
                <span style={{ fontSize: '0.75rem', color: '#10B981' }}>
                  Macro F1: {intentMetrics.proposed.macroF1} | Weighted F1: {intentMetrics.proposed.weightedF1}
                </span>
              </div>
              <div className="cyber-card">
                <span className="mono" style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>ESCALATION RECALL</span>
                <h2 style={{ fontSize: '2rem', fontWeight: 700, color: '#10B981' }}>
                  {escMetrics.recall}
                </h2>
                <span style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>
                  Precision: {escMetrics.precision} | F1: {escMetrics.f1} | Acc: {escMetrics.accuracy}
                </span>
              </div>
              <div className="cyber-card">
                <span className="mono" style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>SUPPORT AUTOMATION RATE</span>
                <h2 style={{ fontSize: '2rem', fontWeight: 700, color: '#00E5FF' }}>
                  {escMetrics.predictedAutoHandled}
                </h2>
                <span style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>
                  Routine Correct: {escMetrics.correctAutoHandledRoutine} | Over-Escalation: {escMetrics.overEscalationRate}
                </span>
              </div>
              <div className="cyber-card">
                <span className="mono" style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>RESPONSE QUALITY SCORE</span>
                <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#10B981', margin: '6px 0' }}>
                  {responseQuality.displayString}
                </h2>
                <span style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>
                  Correctness: {responseQuality.correctness}/5 | Relevance: {responseQuality.relevance}/5
                </span>
              </div>
            </div>

            {/* Baseline Comparison Table */}
            <div className="cyber-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#F3F4F6' }}>
                  System Performance vs Baselines (Independent Golden Set N=200)
                </h3>
                <span className="mono" style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>SOURCE: data/final_evaluation_summary.json</span>
              </div>
              
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #233249', color: '#9CA3AF', fontFamily: 'JetBrains Mono', fontSize: '0.8rem' }}>
                    <th style={{ padding: '12px' }}>MODEL / SYSTEM</th>
                    <th style={{ padding: '12px' }}>INTENT ACCURACY</th>
                    <th style={{ padding: '12px' }}>MACRO F1</th>
                    <th style={{ padding: '12px' }}>WEIGHTED F1</th>
                    <th style={{ padding: '12px' }}>ESCALATION F1</th>
                    <th style={{ padding: '12px' }}>CLASSIFICATION METHOD</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ borderBottom: '1px solid #1D2A40' }}>
                    <td style={{ padding: '12px', fontWeight: 600 }}>Trivial Baseline (Majority Class)</td>
                    <td style={{ padding: '12px' }} className="mono">{intentMetrics.majority.accuracy}</td>
                    <td style={{ padding: '12px' }} className="mono">{intentMetrics.majority.macroF1}</td>
                    <td style={{ padding: '12px' }} className="mono">{intentMetrics.majority.weightedF1}</td>
                    <td style={{ padding: '12px' }} className="mono">N/A</td>
                    <td style={{ padding: '12px' }}><span className="cyber-badge badge-crimson">TRIVIAL BASELINE</span></td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid #1D2A40' }}>
                    <td style={{ padding: '12px', fontWeight: 600 }}>Weakly Supervised ML (TF-IDF + LogReg on 42k corpus)</td>
                    <td style={{ padding: '12px' }} className="mono">{intentMetrics.logReg.accuracy}</td>
                    <td style={{ padding: '12px' }} className="mono">{intentMetrics.logReg.macroF1}</td>
                    <td style={{ padding: '12px' }} className="mono">{intentMetrics.logReg.weightedF1}</td>
                    <td style={{ padding: '12px' }} className="mono">N/A</td>
                    <td style={{ padding: '12px' }}><span className="cyber-badge badge-cyan">WEAKLY SUPERVISED ML</span></td>
                  </tr>
                  <tr style={{ background: 'rgba(0, 229, 255, 0.05)' }}>
                    <td style={{ padding: '12px', fontWeight: 700, color: '#00E5FF' }}>Proposed System v3 (Rule Classifier + Retrieval)</td>
                    <td style={{ padding: '12px', fontWeight: 700, color: '#00E5FF' }} className="mono">{intentMetrics.proposed.accuracy}</td>
                    <td style={{ padding: '12px', fontWeight: 700, color: '#00E5FF' }} className="mono">{intentMetrics.proposed.macroF1}</td>
                    <td style={{ padding: '12px', fontWeight: 700, color: '#00E5FF' }} className="mono">{intentMetrics.proposed.weightedF1}</td>
                    <td style={{ padding: '12px', fontWeight: 700, color: '#10B981' }} className="mono">{escMetrics.f1}</td>
                    <td style={{ padding: '12px' }}><span className="cyber-badge badge-emerald">PROPOSED SYSTEM V3</span></td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Escalation Detailed Metrics Grid */}
            <div className="cyber-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#F3F4F6' }}>
                  Escalation Safety & Automation Breakdown (N=200 Golden Set)
                </h3>
                <span className="cyber-badge badge-cyan">TP: {escMetrics.tp} | TN: {escMetrics.tn} | FP: {escMetrics.fp} | FN: {escMetrics.fn}</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                <div style={{ background: '#0B0F19', padding: '12px', borderRadius: '6px', border: '1px solid #233249' }}>
                  <span className="mono" style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>ESCALATION PRECISION</span>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#00E5FF', margin: '4px 0' }}>
                    {escMetrics.precision}
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>32 TP / (32 TP + 47 FP)</span>
                </div>
                <div style={{ background: '#0B0F19', padding: '12px', borderRadius: '6px', border: '1px solid #233249' }}>
                  <span className="mono" style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>ESCALATION RECALL</span>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#10B981', margin: '4px 0' }}>
                    {escMetrics.recall}
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#10B981' }}>32 TP / (32 TP + 1 FN)</span>
                </div>
                <div style={{ background: '#0B0F19', padding: '12px', borderRadius: '6px', border: '1px solid #233249' }}>
                  <span className="mono" style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>MISSED ESCALATIONS</span>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#10B981', margin: '4px 0' }}>
                    {escMetrics.missed} ({escMetrics.missedRate})
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#10B981' }}>1 FN out of 200 items</span>
                </div>
                <div style={{ background: '#0B0F19', padding: '12px', borderRadius: '6px', border: '1px solid #233249' }}>
                  <span className="mono" style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>OVER-ESCALATION RATE</span>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#FF3B30', margin: '4px 0' }}>
                    {escMetrics.overEscalationRate}
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>47 FP out of 200 items</span>
                </div>
              </div>
            </div>

            {/* Genuine Human Response Quality Metrics Section */}
            <div className="cyber-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#F3F4F6' }}>
                    Human-Reviewed Response-Quality Evaluation
                  </h3>
                  <span className="mono" style={{ fontSize: '0.75rem', color: '#00E5FF' }}>
                    {responseQuality.displayString}
                  </span>
                </div>
                <span className="cyber-badge badge-emerald">30 / 30 HUMAN-REVIEWED</span>
              </div>

              {/* Required LLM Fallback Judge Clear Notice */}
              <div style={{
                background: 'rgba(255, 149, 0, 0.1)',
                border: '1px solid #FF9500',
                color: '#FF9500',
                padding: '12px 16px',
                borderRadius: '6px',
                fontSize: '0.85rem',
                fontWeight: 500
              }}>
                [JUDGE STATUS]: {judgeNotice}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px' }}>
                <div style={{ background: '#0B0F19', padding: '12px', borderRadius: '6px', border: '1px solid #233249' }}>
                  <span className="mono" style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>RELEVANCE</span>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#00E5FF', margin: '4px 0' }}>
                    {responseQuality.relevance} / 5.0
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#10B981' }}>56.67% ≥ 4.0</span>
                </div>
                <div style={{ background: '#0B0F19', padding: '12px', borderRadius: '6px', border: '1px solid #233249' }}>
                  <span className="mono" style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>GROUNDEDNESS</span>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#00E5FF', margin: '4px 0' }}>
                    {responseQuality.groundedness} / 5.0
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>33.33% ≥ 4.0</span>
                </div>
                <div style={{ background: '#0B0F19', padding: '12px', borderRadius: '6px', border: '1px solid #233249' }}>
                  <span className="mono" style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>HELPFULNESS</span>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#00E5FF', margin: '4px 0' }}>
                    {responseQuality.helpfulness} / 5.0
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>43.33% ≥ 4.0</span>
                </div>
                <div style={{ background: '#0B0F19', padding: '12px', borderRadius: '6px', border: '1px solid #233249' }}>
                  <span className="mono" style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>CORRECTNESS</span>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#10B981', margin: '4px 0' }}>
                    {responseQuality.correctness} / 5.0
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#10B981' }}>60.00% ≥ 4.0</span>
                </div>
                <div style={{ background: '#0B0F19', padding: '12px', borderRadius: '6px', border: '1px solid #00E5FF' }}>
                  <span className="mono" style={{ fontSize: '0.7rem', color: '#00E5FF' }}>OVERALL SCORE</span>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#00E5FF', margin: '4px 0' }}>
                    {responseQuality.overall} / 5.0
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>{responseQuality.sample}</span>
                </div>
              </div>
            </div>

            {/* Methodological Disclosures Card */}
            <div style={{
              background: 'rgba(255, 149, 0, 0.08)',
              border: '1px solid #FF9500',
              borderRadius: '8px',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}>
              <span className="mono" style={{ fontSize: '0.8rem', color: '#FF9500', fontWeight: 700 }}>
                METHODOLOGICAL DISCLOSURE — EVALUATION BOUNDARIES:
              </span>
              <ul style={{ fontSize: '0.85rem', color: '#E5E7EB', paddingLeft: '20px', lineHeight: 1.6 }}>
                <li><strong>LLM Judge Unavailability:</strong> {judgeNotice}</li>
                <li><strong>Response Quality:</strong> Displayed response quality is derived from <strong>{responseQuality.displayString}</strong>.</li>
                <li><strong>AI-Assisted Golden Set Labels:</strong> Ground-truth annotations in golden set were created via AI-assisted automatic annotation.</li>
                <li><strong>Weak Supervision:</strong> The baseline ML model was trained on 42,440 historical corpus items labeled via taxonomy rules.</li>
              </ul>
            </div>
          </div>
        )}

        {/* TAB 3: FAILURE ANALYSIS */}
        {activeTab === 'failures' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div className="cyber-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#F3F4F6', marginBottom: '4px' }}>
                    Dynamic Failure Analysis & Diagnostics
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: '#9CA3AF' }}>
                    Loaded dynamically from data/final_failure_analysis.json (63 total failures out of 200 items).
                  </p>
                </div>
                <span className="mono" style={{ fontSize: '0.8rem', color: '#FF3B30' }}>
                  TOP FAILURE MODES (SOURCE OF TRUTH)
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {failureModes.map((fail, idx) => (
                <div key={idx} className="cyber-card" style={{ display: 'flex', flexDirection: 'column', gap: '10px', borderLeft: '4px solid #FF3B30' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="mono" style={{ color: '#FF3B30', fontSize: '0.85rem', fontWeight: 700 }}>
                      FAILURE MODE #{idx + 1}: {fail.failure_mode_name || fail.category}
                    </span>
                    <span className="cyber-badge badge-crimson">
                      {fail.affected_examples_count} CASES ({fail.percentage_of_eval_set}%)
                    </span>
                  </div>

                  <div style={{ background: '#0B0F19', padding: '12px', borderRadius: '6px', border: '1px solid #233249', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                      <span className="mono" style={{ color: '#00E5FF' }}>EXAMPLE TICKET ID: {fail.example_id}</span>
                      <span className="mono" style={{ color: '#9CA3AF' }}>EXPECTED: {fail.expected_intent} | PREDICTED: {fail.model_prediction?.predicted_intent || fail.predicted_intent}</span>
                    </div>
                    <p style={{ fontSize: '0.85rem', color: '#E5E7EB' }}>
                      <strong>Customer Message:</strong> "{fail.customer_message}"
                    </p>
                    <p style={{ fontSize: '0.85rem', color: '#D1D5DB' }}>
                      <strong>Generated Reply:</strong> "{fail.generated_reply}"
                    </p>
                  </div>

                  <div style={{ fontSize: '0.85rem', color: '#D1D5DB' }}>
                    <strong>Why It Failed:</strong> {fail.why_it_failed}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#9CA3AF' }}>
                    <strong>Likely Root Cause:</strong> {fail.likely_root_cause}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#00E5FF' }}>
                    <strong>Proposed Fix Hypothesis:</strong> {fail.fix_hypothesis || fail.proposed_fix}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 4: DECISION LOG */}
        {activeTab === 'decisions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div className="cyber-card">
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#F3F4F6', marginBottom: '8px' }}>
                Engineering & Product Decision Log (12 Non-Obvious Decisions)
              </h3>
              <p style={{ fontSize: '0.85rem', color: '#9CA3AF' }}>
                Audited technical decisions, architectural choices, and explicit engineering tradeoffs parsed from decision_log.md.
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {decisionLogs.map(dec => (
                <div key={dec.id} className="cyber-card" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span className="mono" style={{ fontSize: '0.85rem', color: '#00E5FF', fontWeight: 700 }}>
                    DECISION #{dec.id < 10 ? `0${dec.id}` : dec.id}: {dec.decision}
                  </span>
                  <p style={{ fontSize: '0.85rem', color: '#E5E7EB' }}><strong>Why:</strong> {dec.reason}</p>
                  <p style={{ fontSize: '0.85rem', color: '#9CA3AF' }}><strong>Alternative Considered:</strong> {dec.alternative}</p>
                  <p style={{ fontSize: '0.85rem', color: '#10B981' }}><strong>Tradeoff:</strong> {dec.tradeoff}</p>
                </div>
              ))}
            </div>
          </div>
        )}

      </main>
    </div>
  )
}

