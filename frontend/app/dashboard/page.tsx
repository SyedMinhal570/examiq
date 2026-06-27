"use client"
// app/dashboard/page.tsx — Student Dashboard

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Brain, Play, Clock, Award, TrendingUp, LogOut, BookOpen, AlertTriangle } from "lucide-react"
import toast from "react-hot-toast"
import Cookies from "js-cookie"
import { examApi } from "@/lib/api"
import { useAuthStore } from "@/lib/store"
import { cn, gradeBg, formatDate, thetaToPercent } from "@/lib/utils"
import type { Exam, ExamResult } from "@/types"

export default function DashboardPage() {
  const router = useRouter()
  const { user, clearAuth } = useAuthStore()
  const [exams, setExams] = useState<Exam[]>([])
  const [sessions, setSessions] = useState<ExamResult[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) { router.push("/login"); return }
    if (user.role !== "student") { router.push("/admin"); return }
    loadData()
  }, [user])

  async function loadData() {
    try {
      const [examsData, sessionsData] = await Promise.all([
        examApi.listExams(),
        examApi.getMySessions(),
      ])
      setExams(examsData.exams.filter((e) => e.status === "active"))
      setSessions(sessionsData.sessions)
    } catch {
      toast.error("Failed to load data")
    } finally {
      setLoading(false)
    }
  }

  async function startExam(exam_id: string) {
    try {
      const data = await examApi.startExam(exam_id)
      toast.success("Exam started! Good luck!")
      router.push(`/exam/${data.session_id}`)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to start"
      toast.error(msg)
    }
  }

  function logout() {
    clearAuth()
    Cookies.remove("examiq_token")
    router.push("/login")
  }

  const completedSessions = sessions.filter(s => s.status === "completed")
  const avgTheta = completedSessions.length
    ? completedSessions.reduce((a, s) => a + s.theta_final, 0) / completedSessions.length
    : 0

  if (loading) return <LoadingScreen />

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Nav */}
      <nav className="border-b border-gray-800 bg-gray-950/90 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-blue-400" />
            <span className="font-bold text-white">ExamIQ</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-400">{user?.full_name}</span>
            <span className="badge badge-blue">Student</span>
            <button onClick={logout} className="text-gray-500 hover:text-gray-300 transition-colors">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Greeting */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white">
            Assalamualaikum, {user?.full_name.split(" ")[0]} 👋
          </h1>
          <p className="text-gray-400 mt-1">Ready to test your knowledge adaptively?</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="stat-card">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-2">
              <BookOpen className="w-3.5 h-3.5" /> Exams Taken
            </div>
            <div className="text-2xl font-bold text-white mono">{completedSessions.length}</div>
          </div>
          <div className="stat-card">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-2">
              <TrendingUp className="w-3.5 h-3.5" /> Avg Ability (θ)
            </div>
            <div className="text-2xl font-bold text-blue-400 mono">{avgTheta.toFixed(2)}</div>
          </div>
          <div className="stat-card">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-2">
              <Award className="w-3.5 h-3.5" /> Best Grade
            </div>
            <div className="text-2xl font-bold text-emerald-400">
              {completedSessions.length ? completedSessions[0]?.grade || "–" : "–"}
            </div>
          </div>
          <div className="stat-card">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-2">
              <Clock className="w-3.5 h-3.5" /> Available Exams
            </div>
            <div className="text-2xl font-bold text-white mono">{exams.length}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Available Exams */}
          <div className="lg:col-span-2">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Play className="w-4 h-4 text-blue-400" /> Available Exams
            </h2>

            {exams.length === 0 ? (
              <div className="card text-center py-12 text-gray-500">
                <BookOpen className="w-10 h-10 mx-auto mb-3 opacity-30" />
                <p>No active exams available right now.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {exams.map((exam) => {
                  const alreadyDone = sessions.some(s => s.status === "completed")
                  return (
                    <div key={exam.exam_id} className="card flex items-center justify-between gap-4 p-5">
                      <div>
                        <h3 className="font-semibold text-white">{exam.title}</h3>
                        <div className="flex items-center gap-3 mt-1.5">
                          <span className="badge badge-blue">{exam.subject}</span>
                          <span className="text-xs text-gray-500 flex items-center gap-1">
                            <Clock className="w-3 h-3" /> {exam.time_limit_minutes} min
                          </span>
                          <span className="text-xs text-gray-500">Max {exam.max_items} items</span>
                          {exam.is_adaptive && <span className="badge badge-purple">Adaptive</span>}
                        </div>
                      </div>
                      <button
                        onClick={() => startExam(exam.exam_id)}
                        disabled={alreadyDone}
                        className={cn(
                          "shrink-0 flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
                          alreadyDone
                            ? "bg-gray-800 text-gray-600 cursor-not-allowed"
                            : "bg-blue-600 hover:bg-blue-500 text-white"
                        )}
                      >
                        <Play className="w-3.5 h-3.5" />
                        {alreadyDone ? "Done" : "Start"}
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Past Sessions */}
          <div>
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Clock className="w-4 h-4 text-gray-400" /> Past Sessions
            </h2>
            {sessions.length === 0 ? (
              <div className="card text-center py-8 text-gray-600 text-sm">
                No sessions yet. Take your first exam!
              </div>
            ) : (
              <div className="space-y-3">
                {sessions.slice(0, 8).map((s) => (
                  <Link key={s.session_id} href={`/results/${s.session_id}`}
                    className="card block p-4 hover:border-gray-700 transition-all">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-gray-300 font-medium truncate">{s.exam_title}</span>
                      {s.grade && (
                        <span className={cn("badge border text-xs", gradeBg(s.grade))}>
                          {s.grade}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>θ = {s.theta_final.toFixed(3)}</span>
                      <span>{s.items_administered} items</span>
                    </div>
                    {/* Ability bar */}
                    <div className="mt-2 h-1 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full theta-gradient rounded-full"
                        style={{ width: `${thetaToPercent(s.theta_final)}%` }}
                      />
                    </div>
                    {s.collusion_flag && (
                      <div className="flex items-center gap-1 mt-2 text-xs text-red-400">
                        <AlertTriangle className="w-3 h-3" /> Flagged for review
                      </div>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

function LoadingScreen() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-center">
        <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-gray-400">Loading dashboard...</p>
      </div>
    </div>
  )
}