"use client"
// app/exam/[session_id]/page.tsx — Adaptive Exam Interface

import { useEffect, useState, useCallback, useRef } from "react"
import { useRouter, useParams } from "next/navigation"
import { Brain, Clock, CheckCircle2, XCircle, ChevronRight, AlertCircle } from "lucide-react"
import toast from "react-hot-toast"
import { examApi } from "@/lib/api"
import { cn, thetaToPercent } from "@/lib/utils"
import type { NextQuestionResponse, SubmitAnswerResponse } from "@/types"

type ExamPhase = "loading" | "question" | "feedback" | "submitting" | "complete"

export default function ExamPage() {
  const router = useRouter()
  const params = useParams()
  const session_id = params.session_id as string

  const [phase, setPhase] = useState<ExamPhase>("loading")
  const [question, setQuestion] = useState<NextQuestionResponse | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [openAnswer, setOpenAnswer] = useState("")
  const [feedback, setFeedback] = useState<SubmitAnswerResponse | null>(null)
  const [theta, setTheta] = useState(0)
  const [itemsAnswered, setItemsAnswered] = useState(0)
  const [timeLeft, setTimeLeft] = useState(60)        // seconds per question
  const [totalTime, setTotalTime] = useState(0)       // total elapsed
  const questionStart = useRef<number>(Date.now())
  const timerRef = useRef<NodeJS.Timeout>()

  // Load first question
  useEffect(() => {
    loadNextQuestion()
    // Total time counter
    const totalTimer = setInterval(() => setTotalTime(t => t + 1), 1000)
    return () => clearInterval(totalTimer)
  }, [])

  // Per-question timer
  useEffect(() => {
    if (phase !== "question") { clearInterval(timerRef.current); return }
    setTimeLeft(90)
    timerRef.current = setInterval(() => {
      setTimeLeft(t => {
        if (t <= 1) {
          clearInterval(timerRef.current)
          handleTimeOut()
          return 0
        }
        return t - 1
      })
    }, 1000)
    return () => clearInterval(timerRef.current)
  }, [phase, question?.item_id])

  async function loadNextQuestion() {
    setPhase("loading")
    setSelected(null)
    setOpenAnswer("")
    try {
      const q = await examApi.getNextQuestion(session_id)
      if (q.session_complete) {
        router.push(`/results/${session_id}`)
        return
      }
      setQuestion(q)
      questionStart.current = Date.now()
      setPhase("question")
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 400) {
        // Exam complete
        await examApi.finishExam(session_id)
        router.push(`/results/${session_id}`)
      } else {
        toast.error("Failed to load question")
        setPhase("question")
      }
    }
  }

  async function handleTimeOut() {
    if (!question) return
    toast("Time's up for this question!", { icon: "⏰" })
    await submitAnswer(question, null, "")
  }

  const submitAnswer = useCallback(async (
    q: NextQuestionResponse,
    sel: number | null,
    open: string
  ) => {
    if (phase === "submitting") return
    setPhase("submitting")
    clearInterval(timerRef.current)
    const timeTaken = Math.round((Date.now() - questionStart.current) / 1000)

    try {
      const result = await examApi.submitAnswer(session_id, {
        item_id: q.item_id,
        selected_option: sel,
        open_answer: open || null,
        time_taken_seconds: timeTaken,
      })
      setFeedback(result)
      setTheta(result.theta)
      setItemsAnswered(result.items_answered)
      setPhase("feedback")

      if (result.exam_complete) {
        setTimeout(async () => {
          await examApi.finishExam(session_id)
          router.push(`/results/${session_id}`)
        }, 2500)
      }
    } catch {
      toast.error("Failed to submit answer")
      setPhase("question")
    }
  }, [phase, session_id, router])

  async function handleSubmit() {
    if (!question) return
    if (question.item_type === "mcq" && selected === null) {
      toast.error("Please select an answer")
      return
    }
    await submitAnswer(question, selected, openAnswer)
  }

  const timerPercent = Math.round((timeLeft / 90) * 100)
  const timerColor = timeLeft > 30 ? "bg-blue-500" : timeLeft > 10 ? "bg-yellow-500" : "bg-red-500"

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Top bar */}
      <div className="border-b border-gray-800 bg-gray-900/80 backdrop-blur sticky top-0 z-40">
        <div className="max-w-3xl mx-auto px-6 h-14 flex items-center justify-between gap-6">
          <div className="flex items-center gap-2 shrink-0">
            <Brain className="w-5 h-5 text-blue-400" />
            <span className="font-bold text-white text-sm">ExamIQ</span>
          </div>

          {/* Progress */}
          <div className="flex-1 max-w-xs">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Question {itemsAnswered + (phase === "feedback" ? 0 : 1)}</span>
              <span>θ = <span className="text-blue-400 mono">{theta.toFixed(3)}</span></span>
            </div>
            <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div className="h-full theta-gradient rounded-full transition-all duration-500"
                style={{ width: `${thetaToPercent(theta)}%` }} />
            </div>
          </div>

          {/* Timer */}
          {phase === "question" && (
            <div className="flex items-center gap-2 shrink-0">
              <Clock className="w-3.5 h-3.5 text-gray-500" />
              <div className="w-16 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div className={cn("h-full rounded-full transition-all", timerColor)}
                  style={{ width: `${timerPercent}%` }} />
              </div>
              <span className={cn("mono text-xs", timeLeft <= 10 ? "text-red-400" : "text-gray-400")}>
                {timeLeft}s
              </span>
            </div>
          )}

          {/* Total time */}
          <div className="text-xs text-gray-600 mono shrink-0">
            {Math.floor(totalTime / 60)}:{String(totalTime % 60).padStart(2, "0")}
          </div>
        </div>
      </div>

      {/* Main */}
      <main className="flex-1 max-w-3xl mx-auto px-6 py-10 w-full">

        {/* Loading */}
        {(phase === "loading" || phase === "submitting") && (
          <div className="flex flex-col items-center justify-center h-64 animate-fade-in">
            <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-4" />
            <p className="text-gray-400 text-sm">
              {phase === "loading" ? "Selecting optimal question..." : "Updating ability estimate..."}
            </p>
          </div>
        )}

        {/* Question */}
        {phase === "question" && question && (
          <div className="animate-slide-up">
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-6">
              <span className="badge badge-blue mono">Q{question.question_number}</span>
              <span>Fisher Information maximized at θ = {theta.toFixed(3)}</span>
            </div>

            {/* Question text */}
            <div className="card mb-6">
              <p className="text-white text-lg leading-relaxed">{question.content}</p>
            </div>

            {/* MCQ options */}
            {question.item_type === "mcq" && question.options && (
              <div className="space-y-3 mb-8">
                {question.options.map((opt, i) => (
                  <button key={i} onClick={() => setSelected(i)}
                    className={cn(
                      "w-full text-left p-4 rounded-xl border transition-all duration-150",
                      selected === i
                        ? "bg-blue-600/15 border-blue-500 text-white"
                        : "bg-gray-900 border-gray-800 text-gray-300 hover:border-gray-600 hover:bg-gray-800/50"
                    )}>
                    <span className={cn(
                      "inline-flex items-center justify-center w-6 h-6 rounded-full border text-xs font-bold mr-3",
                      selected === i ? "bg-blue-600 border-blue-500 text-white" : "border-gray-600 text-gray-500"
                    )}>
                      {["A","B","C","D","E"][i]}
                    </span>
                    {opt}
                  </button>
                ))}
              </div>
            )}

            {/* Open-ended */}
            {question.item_type === "open" && (
              <textarea
                className="input min-h-32 mb-8 resize-none"
                placeholder="Type your answer here..."
                value={openAnswer}
                onChange={(e) => setOpenAnswer(e.target.value)}
              />
            )}

            <button onClick={handleSubmit}
              disabled={question.item_type === "mcq" && selected === null}
              className="btn-primary w-full py-3.5 flex items-center justify-center gap-2 text-base">
              Submit Answer <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Feedback */}
        {phase === "feedback" && feedback && question && (
          <div className="animate-slide-up">
            {/* Result banner */}
            <div className={cn(
              "rounded-2xl border p-6 mb-6 flex items-center gap-4",
              feedback.correct === true
                ? "bg-emerald-500/10 border-emerald-500/30"
                : feedback.correct === false
                ? "bg-red-500/10 border-red-500/30"
                : "bg-blue-500/10 border-blue-500/30"
            )}>
              {feedback.correct === true && <CheckCircle2 className="w-8 h-8 text-emerald-400 shrink-0" />}
              {feedback.correct === false && <XCircle className="w-8 h-8 text-red-400 shrink-0" />}
              {feedback.correct === null && <AlertCircle className="w-8 h-8 text-blue-400 shrink-0" />}
              <div>
                <p className={cn("font-semibold text-lg",
                  feedback.correct === true ? "text-emerald-300" :
                  feedback.correct === false ? "text-red-300" : "text-blue-300")}>
                  {feedback.correct === true ? "Correct!" :
                   feedback.correct === false ? "Incorrect" : "Answer recorded"}
                </p>
                <p className="text-gray-400 text-sm mt-0.5">{feedback.message}</p>
              </div>
            </div>

            {/* Ability update */}
            <div className="card mb-6">
              <p className="text-xs text-gray-500 mb-3 uppercase tracking-wider">Ability Update</p>
              <div className="flex items-center justify-between mb-3">
                <span className="text-2xl font-bold mono text-blue-400">θ = {feedback.theta.toFixed(4)}</span>
                <span className="text-sm text-gray-500">SE = ±{feedback.theta_se.toFixed(3)}</span>
              </div>
              <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
                <div className="h-full theta-gradient rounded-full transition-all duration-700"
                  style={{ width: `${thetaToPercent(feedback.theta)}%` }} />
              </div>
              <div className="flex justify-between text-xs text-gray-600 mt-1">
                <span>Low (-4)</span><span>Average (0)</span><span>High (+4)</span>
              </div>
            </div>

            {feedback.exam_complete ? (
              <div className="card text-center py-8">
                <div className="text-3xl mb-2">🎉</div>
                <p className="text-white font-semibold text-lg">Exam Complete!</p>
                <p className="text-gray-400 text-sm mt-1">Final Grade: <span className="text-emerald-400 font-bold">{feedback.grade}</span> · Percentile: <span className="text-blue-400 font-bold">{feedback.percentile}th</span></p>
                <p className="text-gray-600 text-xs mt-3">Redirecting to results...</p>
              </div>
            ) : (
              <button onClick={loadNextQuestion}
                className="btn-primary w-full py-3.5 flex items-center justify-center gap-2 text-base">
                Next Question <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </main>
    </div>
  )
}