"use client"
// app/results/[session_id]/page.tsx

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { Brain, Award, TrendingUp, Clock, AlertTriangle, CheckCircle2, ArrowLeft, Share2 } from "lucide-react"
import { examApi } from "@/lib/api"
import { cn, gradeBg, thetaToPercent, formatDate, formatDuration } from "@/lib/utils"
import type { ExamResult } from "@/types"

export default function ResultsPage() {
  const params = useParams()
  const router = useRouter()
  const session_id = params.session_id as string
  const [result, setResult] = useState<ExamResult | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadResult() }, [])

  async function loadResult() {
    try {
      const data = await examApi.getResult(session_id)
      setResult(data)
    } catch {
      router.push("/dashboard")
    } finally {
      setLoading(false)
    }
  }

  if (loading || !result) return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  const thetaPct = thetaToPercent(result.theta_final)
  const isHigh = result.theta_final > 1
  const duration = result.completed_at
    ? formatDuration(result.started_at, result.completed_at)
    : "–"

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Nav */}
      <nav className="border-b border-gray-800 bg-gray-950/90 backdrop-blur sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors">
            <ArrowLeft className="w-4 h-4" /> Back to dashboard
          </Link>
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-blue-400" />
            <span className="font-bold text-white text-sm">ExamIQ</span>
          </div>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-10 animate-fade-in">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="text-5xl mb-4">{isHigh ? "🎉" : "📊"}</div>
          <h1 className="text-3xl font-bold text-white mb-2">{result.exam_title}</h1>
          <p className="text-gray-400">{result.student_name} · {formatDate(result.started_at)}</p>
        </div>

        {/* Main stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {/* Grade */}
          <div className="card text-center">
            <div className="text-sm text-gray-500 mb-2">Final Grade</div>
            <div className={cn("text-5xl font-bold mb-1", result.grade.startsWith("A") ? "text-emerald-400" : result.grade.startsWith("B") ? "text-blue-400" : "text-yellow-400")}>
              {result.grade}
            </div>
            <div className="text-xs text-gray-600">IRT-based ability estimate</div>
          </div>

          {/* Percentile */}
          <div className="card text-center">
            <div className="text-sm text-gray-500 mb-2">Percentile Rank</div>
            <div className="text-5xl font-bold text-blue-400 mb-1">{thetaPct}<span className="text-2xl">th</span></div>
            <div className="text-xs text-gray-600">Among all test-takers</div>
          </div>

          {/* Score */}
          <div className="card text-center">
            <div className="text-sm text-gray-500 mb-2">Correct Answers</div>
            <div className="text-5xl font-bold text-white mb-1">{Math.round(result.score_percent)}<span className="text-2xl text-gray-500">%</span></div>
            <div className="text-xs text-gray-600">{result.items_administered} adaptive questions</div>
          </div>
        </div>

        {/* Ability Meter */}
        <div className="card mb-6">
          <div className="flex justify-between items-center mb-3">
            <div>
              <p className="font-semibold text-white">Ability Estimate (θ)</p>
              <p className="text-xs text-gray-500 mt-0.5">3PL IRT Maximum Likelihood Estimation</p>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold mono text-blue-400">{result.theta_final.toFixed(4)}</div>
              <div className="text-xs text-gray-600">Standard normal scale</div>
            </div>
          </div>

          <div className="h-4 bg-gray-800 rounded-full overflow-hidden mb-2">
            <div className="h-full theta-gradient rounded-full transition-all duration-1000"
              style={{ width: `${thetaPct}%` }} />
          </div>

          <div className="flex justify-between text-xs text-gray-600">
            <span>Below Average (θ = -4)</span>
            <span className="text-gray-400">Population Mean (θ = 0)</span>
            <span>Exceptional (θ = +4)</span>
          </div>
        </div>

        {/* Details grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="stat-card">
            <div className="text-xs text-gray-500 mb-1 flex items-center gap-1"><TrendingUp className="w-3 h-3"/>Items</div>
            <div className="text-xl font-bold mono text-white">{result.items_administered}</div>
            <div className="text-xs text-gray-600 mt-0.5">vs 100 in fixed exam</div>
          </div>
          <div className="stat-card">
            <div className="text-xs text-gray-500 mb-1 flex items-center gap-1"><Clock className="w-3 h-3"/>Duration</div>
            <div className="text-xl font-bold mono text-white">{duration}</div>
          </div>
          <div className="stat-card">
            <div className="text-xs text-gray-500 mb-1 flex items-center gap-1"><Award className="w-3 h-3"/>Confidence</div>
            <div className="text-xl font-bold mono text-white">{thetaPct}%</div>
            <div className="text-xs text-gray-600 mt-0.5">Percentile rank</div>
          </div>
          <div className="stat-card">
            <div className="text-xs text-gray-500 mb-1">Status</div>
            <div className={cn("text-sm font-semibold mt-1", result.collusion_flag ? "text-red-400" : "text-emerald-400")}>
              {result.collusion_flag ? "⚠ Flagged" : "✓ Clean"}
            </div>
          </div>
        </div>

        {/* Collusion warning */}
        {result.collusion_flag && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-5 mb-6 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-red-300">Academic Integrity Flag</p>
              <p className="text-sm text-gray-400 mt-1">
                This session has been flagged for potential collusion by our GNN anti-cheat system
                (probability: {((result.collusion_probability || 0) * 100).toFixed(1)}%).
                Your faculty will review this. If this is a mistake, contact your instructor.
              </p>
            </div>
          </div>
        )}

        {/* How CAT worked */}
        <div className="card mb-8">
          <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
            <Brain className="w-4 h-4 text-blue-400" /> How the Adaptive Engine Worked for You
          </h3>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
              <p className="text-sm text-gray-300">
                Started at <span className="mono text-blue-400">θ = 0.000</span> (average ability assumption)
              </p>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
              <p className="text-sm text-gray-300">
                Each of your <span className="text-white font-medium">{result.items_administered} questions</span> was
                selected by maximizing Fisher Information at your current θ
              </p>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
              <p className="text-sm text-gray-300">
                Final estimate: <span className="mono text-blue-400">θ = {result.theta_final.toFixed(4)}</span>,
                which puts you at the <span className="text-white font-medium">{thetaPct}th percentile</span>
              </p>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
              <p className="text-sm text-gray-300">
                A fixed exam would have given you ~100 questions for the same measurement accuracy.
                CAT used only <span className="text-white font-medium">{result.items_administered}</span> — saving you{" "}
                <span className="text-emerald-400 font-medium">~{Math.round(100 - result.items_administered)} questions</span>.
              </p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <Link href="/dashboard" className="btn-secondary flex-1 text-center py-3">
            Back to Dashboard
          </Link>
          <button
            onClick={() => navigator.share?.({ title: "ExamIQ Result", text: `I scored ${result.grade} (${thetaPct}th percentile) on ${result.exam_title}!` })}
            className="btn-secondary px-4 py-3 flex items-center gap-2">
            <Share2 className="w-4 h-4" /> Share
          </button>
        </div>
      </main>
    </div>
  )
}