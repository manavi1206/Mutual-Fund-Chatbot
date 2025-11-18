'use client'

import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import styles from './page.module.css'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sourceUrl?: string
  queryType?: string
  conflictDetected?: boolean
  conflictInfo?: any
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hi! I\'m your HDFC Mutual Fund assistant. Ask me factual questions about HDFC schemes like expense ratios, exit loads, fund managers, investment strategies, and more. I provide information only, not investment advice.',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setLoading(true)

    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: userMessage }),
      })

      const data = await response.json()

      if (data.error) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: `Sorry, I encountered an error: ${data.error}. Please try again.`,
          },
        ])
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: data.answer,
            sourceUrl: data.source_url,
            queryType: data.query_type,
            conflictDetected: data.conflict_detected,
            conflictInfo: data.conflict_info,
          },
        ])
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again later.',
        },
      ])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const exampleQuestions = [
    'What is the expense ratio of HDFC Large Cap Fund?',
    'Who manages the HDFC Flexi Cap Fund?',
    'What is the exit load for HDFC ELSS?',
    'What is the investment strategy of HDFC Hybrid Equity Fund?',
    'How do I redeem my HDFC Large Cap Fund units?',
  ]

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div className={styles.logo}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2L2 7L12 12L22 7L12 2Z"
                fill="var(--groww-primary)"
              />
              <path
                d="M2 17L12 22L22 17"
                stroke="var(--groww-primary)"
                strokeWidth="2"
              />
              <path
                d="M2 12L12 17L22 12"
                stroke="var(--groww-primary)"
                strokeWidth="2"
              />
            </svg>
            <span className={styles.logoText}>Groww</span>
          </div>
          <h1 className={styles.headerTitle}>HDFC Mutual Fund FAQ</h1>
        </div>
      </header>

      {/* Main Chat Area */}
      <main className={styles.main}>
        <div className={styles.chatContainer}>
          {messages.length === 1 && (
            <div className={styles.welcomeSection}>
              <h2 className={styles.welcomeTitle}>
                Ask me about HDFC Mutual Funds
              </h2>
              <p className={styles.welcomeSubtitle}>
                Get factual answers from official documents
              </p>
              <div className={styles.exampleQuestions}>
                <p className={styles.exampleLabel}>Try asking:</p>
                <div className={styles.exampleGrid}>
                  {exampleQuestions.map((question, idx) => (
                    <button
                      key={idx}
                      className={styles.exampleButton}
                      onClick={() => {
                        setInput(question)
                        inputRef.current?.focus()
                      }}
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </div>
              <div className={styles.disclaimer}>
                <p>
                  <strong>Note:</strong> I provide factual information only, not
                  investment advice. For personalized guidance, consult a
                  registered financial advisor.
                </p>
              </div>
            </div>
          )}

          <div className={styles.messages}>
            {messages.map((message, idx) => (
              <div
                key={idx}
                className={`${styles.message} ${
                  message.role === 'user' ? styles.userMessage : styles.assistantMessage
                }`}
              >
                <div className={styles.messageContent}>
                  {message.role === 'assistant' && (
                    <div className={styles.assistantAvatar}>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" fill="var(--groww-primary)" />
                        <path
                          d="M8 12L11 15L16 9"
                          stroke="white"
                          strokeWidth="2"
                          strokeLinecap="round"
                        />
                      </svg>
                    </div>
                  )}
                    <div className={styles.messageText}>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        h1: ({node, ...props}) => <h1 style={{fontSize: '1.5rem', fontWeight: 600, marginTop: '1rem', marginBottom: '0.5rem'}} {...props} />,
                        h2: ({node, ...props}) => <h2 style={{fontSize: '1.25rem', fontWeight: 600, marginTop: '0.75rem', marginBottom: '0.5rem'}} {...props} />,
                        h3: ({node, ...props}) => <h3 style={{fontSize: '1.125rem', fontWeight: 600, marginTop: '0.75rem', marginBottom: '0.5rem'}} {...props} />,
                        p: ({node, ...props}) => <p style={{marginBottom: '0.75rem', lineHeight: '1.6'}} {...props} />,
                        ul: ({node, ...props}) => <ul style={{marginBottom: '0.75rem', paddingLeft: '1.5rem'}} {...props} />,
                        ol: ({node, ...props}) => <ol style={{marginBottom: '0.75rem', paddingLeft: '1.5rem'}} {...props} />,
                        li: ({node, ...props}) => <li style={{marginBottom: '0.25rem', lineHeight: '1.6'}} {...props} />,
                        strong: ({node, ...props}) => <strong style={{fontWeight: 600, color: 'inherit'}} {...props} />,
                        a: ({node, ...props}) => <a style={{color: 'var(--groww-primary)', textDecoration: 'underline'}} target="_blank" rel="noopener noreferrer" {...props} />,
                      }}
                    >
                      {message.content.replace(
                        /\[Source\]\((.*?)\)/g,
                        '' // Remove [Source] markdown links - we'll use the sourceUrl prop instead
                      )}
                    </ReactMarkdown>
                    {message.sourceUrl && (
                      <div className={styles.sourceContainer}>
                        <a
                          href={message.sourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={styles.sourceLink}
                        >
                          View Source →
                        </a>
                        {message.sourceUrl.includes('hdfcfund.com') && !message.sourceUrl.includes('.pdf') && (
                          <span className={styles.sourceNote}>
                            (Source website may be temporarily unavailable)
                          </span>
                        )}
                      </div>
                    )}
                    {message.conflictDetected && (
                      <div className={styles.conflictWarning}>
                        <span>⚠️</span> Conflict detected: Different sources
                        have different values. Using authoritative source.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {loading && (
              <div className={`${styles.message} ${styles.assistantMessage}`}>
                <div className={styles.messageContent}>
                  <div className={styles.assistantAvatar}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" fill="var(--groww-primary)" />
                    </svg>
                  </div>
                  <div className={styles.loadingDots}>
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className={styles.inputContainer}>
          <form onSubmit={handleSubmit} className={styles.inputForm}>
            <div className={styles.inputWrapper}>
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about HDFC Mutual Funds..."
                className={styles.input}
                rows={1}
                disabled={loading}
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className={styles.sendButton}
                aria-label="Send message"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
              </button>
            </div>
            <p className={styles.inputHint}>
              Press Enter to send, Shift+Enter for new line
            </p>
          </form>
        </div>
      </main>
    </div>
  )
}

