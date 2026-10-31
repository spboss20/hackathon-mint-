import { useEffect, useRef, useState } from 'react'
import { Mic, MicOff, Volume2, Radio, Wifi, WifiOff, Trash2 } from 'lucide-react'
import api from '../services/api'
import PageHeader from '../components/PageHeader'

const WS_URL = (import.meta.env.VITE_VOICE_WS_URL || 'ws://localhost:8000/ws/voice')
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition

function guessLanguage(text) {
  // Reliable script-level detection for Devanagari; Roman Hinglish needs an
  // actual multilingual speech-recognition provider on the backend.
  return /[\u0900-\u097F]/.test(text) ? 'hi-IN' : 'en-IN'
}

export default function VoiceAgent() {
  const [customer, setCustomer] = useState('Website Customer')
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'Hi! I’m your SupportIQ voice assistant. Start speaking whenever you’re ready.' }
  ])
  const [draft, setDraft] = useState('')
  const [listening, setListening] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [connected, setConnected] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [error, setError] = useState('')
  const [lastLanguage, setLastLanguage] = useState('Auto')
  const [ticket, setTicket] = useState(null)
  const recognitionRef = useRef(null)
  const socketRef = useRef(null)
  const silenceRef = useRef(null)
  const listeningRef = useRef(false)
  const draftRef = useRef('')
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => () => {
    listeningRef.current = false
    clearTimeout(silenceRef.current)
    recognitionRef.current?.stop()
    socketRef.current?.close()
    window.speechSynthesis?.cancel()
  }, [])

  function addMessage(message) {
    setMessages(prev => [...prev, message])
  }

  function speakReply(text, lang = 'en-IN') {
    if (!('speechSynthesis' in window) || !text) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = lang
    utterance.rate = 1
    utterance.onstart = () => setSpeaking(true)
    utterance.onend = () => setSpeaking(false)
    utterance.onerror = () => setSpeaking(false)
    window.speechSynthesis.speak(utterance)
  }

  function handleAssistantReply(data) {
    const reply = data.reply || data.message || data.text
    if (!reply) return
    addMessage({ role: 'assistant', text: reply, meta: data })
    setTicket(data.ticket_id ? data : null)
    const replyLang = data.language === 'hi' || data.language === 'hi-IN' ? 'hi-IN'
      : data.language === 'en' || data.language === 'en-IN' ? 'en-IN'
      : guessLanguage(reply)
    speakReply(reply, replyLang)
  }

  function sendUtterance(text) {
    const clean = text.trim()
    if (!clean) return
    const lang = guessLanguage(clean)
    setLastLanguage(lang === 'hi-IN' ? 'Hindi / Devanagari' : 'English / Roman')
    addMessage({ role: 'user', text: clean })
    setDraft('')
    draftRef.current = ''

    const payload = {
      type: 'user_message',
      customer_name: customer,
      message: clean,
      source: 'browser_voice',
      language_hint: lang
    }

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(payload))
      return
    }

    // Fallback keeps compatibility with the existing REST API, but it is
    // request/response rather than a persistent real-time voice session.
    api.post('/api/chat', {
      customer_name: customer,
      message: clean,
      source: 'browser_voice'
    }).then(({ data }) => handleAssistantReply(data))
      .catch(() => setError('Could not reach the backend. Start FastAPI and check the API URL.'))
  }

  function startRecognition() {
    if (!SpeechRecognition) {
      setError('Speech recognition is not supported in this browser. Please use the latest Chrome or Edge.')
      return
    }
    const recognition = new SpeechRecognition()
    recognition.lang = 'en-IN'
    recognition.continuous = true
    recognition.interimResults = true
    recognition.maxAlternatives = 1

    recognition.onstart = () => {
      setListening(true)
      listeningRef.current = true
      setError('')
    }

    recognition.onresult = event => {
      let finalText = ''
      let interimText = ''
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const transcript = event.results[i][0].transcript
        if (event.results[i].isFinal) finalText += transcript
        else interimText += transcript
      }
      if (finalText.trim()) {
        draftRef.current = `${draftRef.current} ${finalText}`.trim()
        setDraft(draftRef.current)
        clearTimeout(silenceRef.current)
        silenceRef.current = setTimeout(() => {
          const ready = draftRef.current
          if (ready) sendUtterance(ready)
        }, 900)
      } else if (interimText) {
        setDraft(`${draftRef.current} ${interimText}`.trim())
      }
    }

    recognition.onerror = event => {
      if (event.error !== 'no-speech' && event.error !== 'aborted') {
        setError(`Microphone recognition issue: ${event.error}. Check browser microphone permission.`)
      }
    }

    recognition.onend = () => {
      setListening(false)
      if (listeningRef.current) {
        try { recognition.start() } catch { /* browser may still be shutting down */ }
      }
    }

    recognitionRef.current = recognition
    try {
      recognition.start()
    } catch {
      setError('Could not start microphone. Please allow microphone access and try again.')
    }
  }

  function startSession() {
    if (listeningRef.current) return
    setError('')
    setConnecting(true)

    // WebSocket is the real-time backend path. If it is not available,
    // REST fallback remains usable but is not a full-duplex voice session.
    try {
      const ws = new WebSocket(WS_URL)
      socketRef.current = ws
      ws.onopen = () => {
        setConnected(true)
        setConnecting(false)
        ws.send(JSON.stringify({ type: 'start_session', customer_name: customer }))
        startRecognition()
      }
      ws.onmessage = event => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'assistant_message' || data.reply || data.text) handleAssistantReply(data)
          else if (data.type === 'error') setError(data.message || 'Voice session error.')
        } catch {
          setError('Received an unreadable response from the voice server.')
        }
      }
      ws.onerror = () => {
        setConnected(false)
        setConnecting(false)
        setError('Real-time voice socket is unavailable. Using REST chat fallback when you speak. Add the /ws/voice backend route for live sessions.')
        startRecognition()
      }
      ws.onclose = () => setConnected(false)
    } catch {
      setConnecting(false)
      setError('Could not open real-time voice connection. REST fallback will be used.')
      startRecognition()
    }
  }

  function stopSession() {
    listeningRef.current = false
    clearTimeout(silenceRef.current)
    recognitionRef.current?.stop()
    recognitionRef.current = null
    setListening(false)
    window.speechSynthesis?.cancel()
    setSpeaking(false)
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'end_session' }))
    }
    socketRef.current?.close()
    socketRef.current = null
    setConnected(false)
    setConnecting(false)
  }

  function submitDraft() {
    clearTimeout(silenceRef.current)
    const text = draftRef.current || draft
    if (text.trim()) sendUtterance(text)
  }

  return (
    <div className="page p-8">
      <PageHeader title="AI Voice Agent" subtitle="Have a hands-free support conversation in English, Hindi, or Hinglish." />

      <div className="mx-auto grid max-w-6xl grid-cols-[1fr_290px] gap-5 max-lg:grid-cols-1">
        <section className="card flex min-h-[650px] flex-col overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b p-5">
            <div className="flex items-center gap-3">
              <span className="rounded-xl bg-blue-50 p-3 text-blue-600"><Radio size={21} /></span>
              <div>
                <b className="text-sm">SupportIQ Live Voice</b>
                <p className="mt-1 text-xs text-slate-400">Speak naturally — no send button needed</p>
              </div>
            </div>
            <span className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-[11px] font-semibold ${connected ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
              {connected ? <Wifi size={13}/> : <WifiOff size={13}/>}
              {connected ? 'Live socket connected' : 'REST / waiting for socket'}
            </span>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto bg-slate-50/60 p-5">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-6 ${m.role === 'user' ? 'bg-blue-600 text-white' : 'border border-slate-100 bg-white text-slate-700 shadow-sm'}`}>
                  <p>{m.text}</p>
                  {m.meta?.ticket_id && <p className="mt-2 border-t border-slate-200 pt-2 text-[10px] text-slate-500">Ticket {m.meta.ticket_id} · {m.meta.category || 'Support'} · {m.meta.priority || 'Normal'} {m.meta.escalate ? '· Escalated' : ''}</p>}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef}/>
          </div>

          <div className="border-t bg-white p-5">
            <label className="mb-2 block text-xs font-semibold text-slate-500">Customer name</label>
            <input className="field mb-4 max-w-sm text-sm" value={customer} onChange={e => setCustomer(e.target.value)} />
            <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-4">
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-blue-700">Live transcript · {lastLanguage}</p>
              <p className="min-h-6 text-sm text-slate-700">{draft || (listening ? 'Listening for your voice…' : 'Your live transcript will appear here.')}</p>
              {draft && <button onClick={submitDraft} className="btn mt-3 text-xs">Send this sentence</button>}
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              {!listening && !connecting
                ? <button onClick={startSession} className="btn"><Mic size={17}/>Start live conversation</button>
                : <button onClick={stopSession} className="inline-flex items-center gap-2 rounded-xl bg-rose-600 px-4 py-2.5 text-sm font-semibold text-white"><MicOff size={17}/>End conversation</button>}
              {connecting && <span className="text-xs text-slate-500">Connecting…</span>}
              {speaking && <span className="flex items-center gap-2 text-xs font-medium text-blue-600"><Volume2 size={15}/>AI is speaking</span>}
              {listening && <span className="flex items-center gap-2 text-xs font-medium text-emerald-600"><span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500"/>Microphone active</span>}
            </div>
            {error && <p className="mt-3 rounded-lg bg-amber-50 p-3 text-xs leading-5 text-amber-800">{error}</p>}
          </div>
        </section>

        <aside className="space-y-4">
          <section className="card p-5">
            <h3 className="font-bold">Voice session</h3>
            <div className="mt-4 space-y-3 text-xs text-slate-500">
              <div className="flex justify-between"><span>Microphone</span><b className={listening ? 'text-emerald-600' : 'text-slate-400'}>{listening ? 'Active' : 'Off'}</b></div>
              <div className="flex justify-between"><span>AI voice</span><b className={speaking ? 'text-blue-600' : 'text-slate-400'}>{speaking ? 'Speaking' : 'Ready'}</b></div>
              <div className="flex justify-between"><span>Language hint</span><b className="text-slate-700">{lastLanguage}</b></div>
            </div>
          </section>
          <section className="card p-5">
            <h3 className="font-bold">What this version supports</h3>
            <ul className="mt-3 space-y-2 text-xs leading-5 text-slate-500">
              <li>• Continuous browser speech recognition while the session is active.</li>
              <li>• Automatically sends detected speech after a short pause.</li>
              <li>• Browser text-to-speech reads the assistant response aloud.</li>
              <li>• Hindi script detection and English fallback language hint.</li>
            </ul>
          </section>
          <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
            <h3 className="text-sm font-bold text-amber-900">Backend requirement</h3>
            <p className="mt-2 text-xs leading-5 text-amber-800">For true real-time multilingual conversation, the backend must implement <code>/ws/voice</code> with streaming speech recognition / multilingual model support. The existing REST <code>/api/chat</code> endpoint is used as a fallback.</p>
          </section>
        </aside>
      </div>
    </div>
  )
}
