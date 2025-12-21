/**
 * Enhanced floating chat bubble with expandable modal and model management.
 * Supports React Markdown for rich text rendering with streaming.
 */

import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { clsx } from 'clsx'
import {
  MessageCircle,
  X,
  Send,
  Loader2,
  ChevronDown,
  Bot,
  User,
  Maximize2,
  Minimize2,
  Trash2,
  Settings,
  Download,
  Check,
  AlertCircle,
  Search,
  RefreshCw,
  Copy,
  CheckCheck,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

/**
 * Code block with copy button and syntax highlighting.
 */
function CodeBlock({ children, className, inline }) {
  const [copied, setCopied] = useState(false)
  const match = /language-(\w+)/.exec(className || '')
  const language = match ? match[1] : ''

  const handleCopy = async () => {
    await navigator.clipboard.writeText(String(children).replace(/\n$/, ''))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (inline) {
    return (
      <code className="px-1.5 py-0.5 bg-slate-200 dark:bg-slate-700 rounded text-sm font-mono text-pink-600 dark:text-pink-400">
        {children}
      </code>
    )
  }

  return (
    <div className="relative group my-3">
      <button
        onClick={handleCopy}
        className="absolute right-2 top-2 p-1.5 bg-slate-700 hover:bg-slate-600 rounded opacity-0 group-hover:opacity-100 transition-opacity"
        title="Copy code"
      >
        {copied ? (
          <CheckCheck className="w-4 h-4 text-emerald-400" />
        ) : (
          <Copy className="w-4 h-4 text-slate-300" />
        )}
      </button>
      {language && (
        <span className="absolute left-3 top-2 text-xs text-slate-400 font-mono">
          {language}
        </span>
      )}
      <SyntaxHighlighter
        style={oneDark}
        language={language || 'text'}
        PreTag="div"
        className="!mt-0 !rounded-lg !text-sm"
        customStyle={{
          margin: 0,
          borderRadius: '0.5rem',
          paddingTop: language ? '2rem' : '1rem',
        }}
      >
        {String(children).replace(/\n$/, '')}
      </SyntaxHighlighter>
    </div>
  )
}

/**
 * Markdown content renderer with custom components.
 */
function MarkdownContent({ content, isStreaming }) {
  const components = useMemo(() => ({
    // Code blocks with syntax highlighting
    code({ node, inline, className, children, ...props }) {
      return (
        <CodeBlock inline={inline} className={className}>
          {children}
        </CodeBlock>
      )
    },
    // Headings
    h1: ({ children }) => (
      <h1 className="text-xl font-bold mt-4 mb-2 text-slate-900 dark:text-white">{children}</h1>
    ),
    h2: ({ children }) => (
      <h2 className="text-lg font-bold mt-3 mb-2 text-slate-900 dark:text-white">{children}</h2>
    ),
    h3: ({ children }) => (
      <h3 className="text-base font-bold mt-3 mb-1 text-slate-900 dark:text-white">{children}</h3>
    ),
    h4: ({ children }) => (
      <h4 className="text-sm font-bold mt-2 mb-1 text-slate-900 dark:text-white">{children}</h4>
    ),
    // Paragraphs
    p: ({ children }) => (
      <p className="mb-2 last:mb-0 text-sm leading-relaxed">{children}</p>
    ),
    // Lists
    ul: ({ children }) => (
      <ul className="list-disc list-inside mb-2 space-y-1 text-sm">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal list-inside mb-2 space-y-1 text-sm">{children}</ol>
    ),
    li: ({ children }) => (
      <li className="text-sm">{children}</li>
    ),
    // Tables
    table: ({ children }) => (
      <div className="overflow-x-auto my-3">
        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700 text-sm">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }) => (
      <thead className="bg-slate-100 dark:bg-slate-800">{children}</thead>
    ),
    tbody: ({ children }) => (
      <tbody className="divide-y divide-slate-200 dark:divide-slate-700">{children}</tbody>
    ),
    tr: ({ children }) => (
      <tr className="hover:bg-slate-50 dark:hover:bg-slate-800/50">{children}</tr>
    ),
    th: ({ children }) => (
      <th className="px-3 py-2 text-left text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="px-3 py-2 text-slate-900 dark:text-white">{children}</td>
    ),
    // Blockquotes
    blockquote: ({ children }) => (
      <blockquote className="border-l-4 border-blue-500 pl-4 py-1 my-2 bg-slate-100 dark:bg-slate-800 rounded-r italic text-sm">
        {children}
      </blockquote>
    ),
    // Links
    a: ({ href, children }) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-blue-600 dark:text-blue-400 hover:underline"
      >
        {children}
      </a>
    ),
    // Horizontal rule
    hr: () => (
      <hr className="my-4 border-slate-200 dark:border-slate-700" />
    ),
    // Strong/Bold
    strong: ({ children }) => (
      <strong className="font-semibold text-slate-900 dark:text-white">{children}</strong>
    ),
    // Emphasis/Italic
    em: ({ children }) => (
      <em className="italic">{children}</em>
    ),
  }), [])

  return (
    <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
      >
        {content}
      </ReactMarkdown>
      {isStreaming && (
        <span className="inline-block w-2 h-4 ml-1 bg-blue-500 animate-pulse rounded-sm" />
      )}
    </div>
  )
}

/**
 * Chat message component with markdown support for assistant messages.
 */
function ChatMessage({ message, isUser, isStreaming }) {
  return (
    <div
      className={clsx(
        'flex gap-3 mb-4',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      <div
        className={clsx(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center mt-1',
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
        )}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>
      <div
        className={clsx(
          'max-w-[85%] rounded-2xl px-4 py-2',
          isUser
            ? 'bg-blue-600 text-white rounded-br-md'
            : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white rounded-bl-md'
        )}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
        ) : (
          <MarkdownContent content={message.content} isStreaming={isStreaming && !message.stats} />
        )}
        {message.stats && (
          <p className="text-xs mt-2 pt-2 border-t border-slate-200 dark:border-slate-700 opacity-70">
            {message.stats.tokens} tokens | {(message.stats.latency / 1000).toFixed(1)}s
          </p>
        )}
      </div>
    </div>
  )
}

/**
 * Model selector dropdown.
 */
function ModelSelector({ models, selectedModel, onSelect, loading, onManageClick }) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={loading}
        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-slate-100 dark:bg-slate-800 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
      >
        <Bot className="w-4 h-4" />
        <span className="truncate max-w-[120px]">{selectedModel}</span>
        <ChevronDown className={clsx('w-4 h-4 transition-transform', isOpen && 'rotate-180')} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-full right-0 mt-2 w-56 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 overflow-hidden z-[100]"
          >
            <div className="max-h-64 overflow-y-auto">
              {models.length === 0 ? (
                <div className="px-3 py-2 text-sm text-slate-500">No models available</div>
              ) : (
                models.map((model) => (
                  <button
                    key={model.name}
                    onClick={() => {
                      onSelect(model.name)
                      setIsOpen(false)
                    }}
                    className={clsx(
                      'w-full text-left px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors flex items-center justify-between',
                      model.name === selectedModel && 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                    )}
                  >
                    <span className="truncate">{model.name}</span>
                    {model.name === selectedModel && <Check className="w-4 h-4 flex-shrink-0" />}
                  </button>
                ))
              )}
            </div>
            <div className="border-t border-slate-200 dark:border-slate-700">
              <button
                onClick={() => {
                  onManageClick()
                  setIsOpen(false)
                }}
                className="w-full text-left px-3 py-2 text-sm text-blue-600 dark:text-blue-400 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2"
              >
                <Settings className="w-4 h-4" />
                Manage Models
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/**
 * Model management panel.
 */
function ModelManagement({ models, onRefresh, onClose }) {
  const [searchQuery, setSearchQuery] = useState('')
  const [libraryModels, setLibraryModels] = useState([])
  const [loading, setLoading] = useState(false)
  const [pulling, setPulling] = useState(null)
  const [pullProgress, setPullProgress] = useState({})
  const [deleting, setDeleting] = useState(null)
  const [error, setError] = useState(null)

  // Fetch library models
  useEffect(() => {
    fetchLibrary()
  }, [])

  const fetchLibrary = async (query = '') => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/ollama/library?q=${encodeURIComponent(query)}`)
      if (response.ok) {
        const data = await response.json()
        setLibraryModels(data.models || [])
      }
    } catch (err) {
      console.error('Failed to fetch library:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e) => {
    const query = e.target.value
    setSearchQuery(query)
    fetchLibrary(query)
  }

  const pullModel = async (modelName) => {
    setPulling(modelName)
    setPullProgress({ [modelName]: { status: 'starting', percent: 0 } })
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/ollama/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: modelName }),
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.error) {
                setError(data.error)
                setPulling(null)
                return
              }
              if (data.status) {
                let percent = 0
                if (data.completed && data.total) {
                  percent = Math.round((data.completed / data.total) * 100)
                }
                setPullProgress({
                  [modelName]: { status: data.status, percent }
                })
              }
            } catch (e) {
              // Ignore parse errors
            }
          }
        }
      }

      // Refresh models list
      onRefresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setPulling(null)
      setPullProgress({})
    }
  }

  const deleteModel = async (modelName) => {
    if (!confirm(`Are you sure you want to delete ${modelName}?`)) return

    setDeleting(modelName)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/ollama/models/${encodeURIComponent(modelName)}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error('Failed to delete model')
      }

      onRefresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setDeleting(null)
    }
  }

  const installedModelNames = models.map(m => m.name.split(':')[0])

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
        <div className="flex items-center gap-2">
          <Download className="w-5 h-5 text-blue-600" />
          <span className="font-semibold text-slate-900 dark:text-white">Model Manager</span>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
        >
          <X className="w-5 h-5 text-slate-500" />
        </button>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-700">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={handleSearch}
            placeholder="Search models (e.g., llama, mistral, code)..."
            className="w-full pl-10 pr-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-600 dark:text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Installed Models */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              Installed Models ({models.length})
            </h3>
            <button
              onClick={onRefresh}
              className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded transition-colors"
            >
              <RefreshCw className="w-4 h-4 text-slate-500" />
            </button>
          </div>
          {models.length === 0 ? (
            <p className="text-sm text-slate-500">No models installed</p>
          ) : (
            <div className="space-y-2">
              {models.map((model) => (
                <div
                  key={model.name}
                  className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg"
                >
                  <div>
                    <p className="font-medium text-slate-900 dark:text-white">{model.name}</p>
                    <p className="text-xs text-slate-500">
                      {model.size ? `${(model.size / 1e9).toFixed(1)} GB` : 'Unknown size'}
                    </p>
                  </div>
                  <button
                    onClick={() => deleteModel(model.name)}
                    disabled={deleting === model.name}
                    className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors disabled:opacity-50"
                  >
                    {deleting === model.name ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Available Models */}
        <div>
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
            Available Models
          </h3>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
            </div>
          ) : (
            <div className="space-y-2">
              {libraryModels.map((model) => {
                const isInstalled = installedModelNames.includes(model.name)
                const isPulling = pulling === model.name
                const progress = pullProgress[model.name]

                return (
                  <div
                    key={model.name}
                    className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-slate-900 dark:text-white">{model.name}</p>
                      <p className="text-xs text-slate-500 truncate">{model.description}</p>
                      <p className="text-xs text-slate-400">Size: {model.size}</p>
                    </div>
                    {isInstalled ? (
                      <span className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 px-2 py-1 bg-emerald-50 dark:bg-emerald-900/30 rounded-full">
                        <Check className="w-3 h-3" />
                        Installed
                      </span>
                    ) : isPulling ? (
                      <div className="flex items-center gap-2">
                        <div className="text-xs text-slate-500 max-w-[100px] truncate">
                          {progress?.status || 'Starting...'}
                        </div>
                        <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                      </div>
                    ) : (
                      <button
                        onClick={() => pullModel(model.name)}
                        className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                      >
                        <Download className="w-3 h-3" />
                        Pull
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * Main chat bubble component with expandable modal.
 */
export function ChatBubble() {
  const [isOpen, setIsOpen] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [showModelManager, setShowModelManager] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState('llama3.2')
  const [modelsLoading, setModelsLoading] = useState(false)

  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Scroll to bottom on new messages
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // Focus input when chat opens
  useEffect(() => {
    if (isOpen && !showModelManager) {
      inputRef.current?.focus()
    }
  }, [isOpen, showModelManager])

  // Fetch available models
  const fetchModels = useCallback(async () => {
    setModelsLoading(true)
    try {
      const response = await fetch(`${API_BASE}/ollama/models`)
      if (response.ok) {
        const data = await response.json()
        setModels(data.models || [])
        if (data.models?.length > 0 && !data.models.find(m => m.name === selectedModel)) {
          setSelectedModel(data.models[0].name)
        }
      }
    } catch (error) {
      console.error('Failed to fetch models:', error)
    } finally {
      setModelsLoading(false)
    }
  }, [selectedModel])

  useEffect(() => {
    if (isOpen && models.length === 0) {
      fetchModels()
    }
  }, [isOpen, models.length, fetchModels])

  // Send message with streaming
  const sendMessage = async () => {
    if (!input.trim() || isStreaming) return

    const userMessage = { role: 'user', content: input.trim() }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsStreaming(true)

    // Add placeholder for assistant message
    const assistantMessage = { role: 'assistant', content: '', stats: null }
    setMessages((prev) => [...prev, assistantMessage])

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: userMessage.content,
          model: selectedModel,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''
      let stats = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              if (data.token) {
                fullContent += data.token
                setMessages((prev) => {
                  const newMessages = [...prev]
                  newMessages[newMessages.length - 1] = {
                    role: 'assistant',
                    content: fullContent,
                    stats: null,
                  }
                  return newMessages
                })
              }

              if (data.done) {
                stats = {
                  tokens: data.completion_tokens,
                  latency: data.latency_ms,
                }
              }

              if (data.error) {
                throw new Error(data.error)
              }
            } catch (e) {
              if (e.message !== 'Unexpected end of JSON input') {
                console.error('Parse error:', e)
              }
            }
          }
        }
      }

      // Update final message with stats
      setMessages((prev) => {
        const newMessages = [...prev]
        newMessages[newMessages.length - 1] = {
          role: 'assistant',
          content: fullContent,
          stats,
        }
        return newMessages
      })
    } catch (error) {
      console.error('Chat error:', error)
      setMessages((prev) => {
        const newMessages = [...prev]
        newMessages[newMessages.length - 1] = {
          role: 'assistant',
          content: `Error: ${error.message}`,
          stats: null,
        }
        return newMessages
      })
    } finally {
      setIsStreaming(false)
    }
  }

  // Handle Enter key
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
    // Escape to close
    if (e.key === 'Escape') {
      if (isExpanded) {
        setIsExpanded(false)
      } else {
        setIsOpen(false)
      }
    }
  }

  // Clear chat
  const clearChat = () => {
    setMessages([])
  }

  // Window size classes
  const windowClasses = isExpanded
    ? 'fixed inset-4 md:inset-8 lg:inset-16 z-50'
    : 'fixed bottom-24 right-6 z-50 w-96 h-[500px]'

  return (
    <>
      {/* Chat bubble button */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          'fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-colors',
          isOpen
            ? 'bg-slate-600 hover:bg-slate-700'
            : 'bg-blue-600 hover:bg-blue-700'
        )}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        {isOpen ? (
          <X className="w-6 h-6 text-white" />
        ) : (
          <MessageCircle className="w-6 h-6 text-white" />
        )}
      </motion.button>

      {/* Chat window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className={clsx(
              windowClasses,
              'bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 flex flex-col overflow-hidden'
            )}
          >
            {showModelManager ? (
              <ModelManagement
                models={models}
                onRefresh={fetchModels}
                onClose={() => setShowModelManager(false)}
              />
            ) : (
              <>
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 relative z-10">
                  <div className="flex items-center gap-2">
                    <Bot className="w-5 h-5 text-blue-600" />
                    <span className="font-semibold text-slate-900 dark:text-white">
                      Chat with Ollama
                    </span>
                  </div>
                  <div className="flex items-center gap-2 relative">
                    <ModelSelector
                      models={models}
                      selectedModel={selectedModel}
                      onSelect={setSelectedModel}
                      loading={modelsLoading}
                      onManageClick={() => setShowModelManager(true)}
                    />
                    <button
                      onClick={() => setIsExpanded(!isExpanded)}
                      className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
                      title={isExpanded ? 'Minimize' : 'Expand'}
                    >
                      {isExpanded ? (
                        <Minimize2 className="w-4 h-4 text-slate-500" />
                      ) : (
                        <Maximize2 className="w-4 h-4 text-slate-500" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4">
                  {messages.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-slate-400 dark:text-slate-500 text-sm text-center">
                      <div>
                        <Bot className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>Start a conversation with {selectedModel}</p>
                        <p className="text-xs mt-2 opacity-70">Press Escape to close</p>
                      </div>
                    </div>
                  ) : (
                    messages.map((message, index) => (
                      <ChatMessage
                        key={index}
                        message={message}
                        isUser={message.role === 'user'}
                        isStreaming={isStreaming && index === messages.length - 1}
                      />
                    ))
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className="p-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                  <div className="flex items-center gap-2">
                    {messages.length > 0 && (
                      <button
                        onClick={clearChat}
                        className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
                        title="Clear chat"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    )}
                    <input
                      ref={inputRef}
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Type a message..."
                      disabled={isStreaming}
                      className="flex-1 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                    />
                    <button
                      onClick={sendMessage}
                      disabled={!input.trim() || isStreaming}
                      className="w-10 h-10 rounded-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 flex items-center justify-center transition-colors"
                    >
                      {isStreaming ? (
                        <Loader2 className="w-5 h-5 text-white animate-spin" />
                      ) : (
                        <Send className="w-5 h-5 text-white" />
                      )}
                    </button>
                  </div>
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Backdrop for expanded mode */}
      <AnimatePresence>
        {isOpen && isExpanded && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-40"
            onClick={() => setIsExpanded(false)}
          />
        )}
      </AnimatePresence>
    </>
  )
}

export default ChatBubble
