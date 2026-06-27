"use client"
// app/admin/page.tsx — Faculty Admin Dashboard

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import {
  Brain, Users, BookOpen, TrendingUp, AlertTriangle,
  Plus, LogOut, BarChart3, Shield, RefreshCw, Eye,
  CheckCircle2, XCircle, Clock
} from "lucide-react"
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid
} from "recharts"
import toast from "react-hot-toast"
import Cookies from "js-cookie"
import { analyticsApi, examApi } from "@/lib/api"
import { useAuthStore } from "@/lib/store"
import { cn, gradeBg, formatDate } from "@/lib/utils"
import type { AnalyticsOverview, Exam, ExamStats } from "@/types"

type ActiveTab = "overview" | "exams" | "items" | "flags"

export default function AdminPage() {
  const router = useRouter()
  const { user, clearAuth } = useAuthStore()
  const [tab, setTab] = useState<ActiveTab>("overview")
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null)
  const [exams, setExams] = useState<Exam[]>([])
  const [selectedExam, setSelectedExam] = useState<string | null>(null)
  const [examStats, setExamStats] = useState<ExamStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) { router.push("/login"); return }
    if (user.role === "student") { router.push("/dashboard"); return }
    loadData()
  }, [user])

  useEffect(() => {
    if (selectedExam) loadExamStats(selectedExam)
  }, [selectedExam])

  async function loadData() {
    setLoading(true)
    try {
      const [ov, ex] = await Promise.all([
        analyticsApi.overview(),
        examApi.listExams(),
      ])
      setOverview(ov)
      setExams(ex.exams)
      if (ex.exams.length > 0) setSelectedExam(ex.exams[0].exam_id)
    } catch { toast.error("Failed to load data") }
    finally { setLoading(false) }
  }

  async function loadExamStats(examId: string) {
    try {
      const stats = await analyticsApi.examStats(examId)
      setExamStats(stats)
    } catch { /* exam might have no sessions yet */ }
  }

  async function publishExam(examId: string) {
    try {
      await analyticsApi.publishExam(examId)
      toast.success("Exam published! Students can now take it.")
      loadData()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to publish"
      toast.error(msg)
    }
  }

  function logout() {
    clearAuth(); Cookies.remove("examiq_token"); router.push("/login")
  }

  // Grade distribution for chart
  const gradeChartData = examStats?.grade_distribution
    ? Object.entries(examStats.grade_distribution).map(([g, c]) => ({ grade: g, count: c }))
    : []

  // Theta histogram data
  const thetaHistData = examStats?.thetas
    ? buildHistogram(examStats.thetas)
    : []

  if (loading) return <LoadingScreen />

  return (
    <div className="min-h-screen bg-gray-950 flex">
      {/* Sidebar */}
      <aside className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col fixed h-full z-40">
        <div className="p-4 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
              <Brain className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-bold text-white text-sm">ExamIQ</span>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold">
              {user?.full_name?.[0] || "F"}
            </div>
            <div>
              <p className="text-white text-xs font-medium truncate">{user?.full_name}</p>
              <span className="badge badge-purple text-xs">Faculty</span>
            </div>
          </div>
        </div>

        <nav className="p-3 flex-1">
          {[
            { id: "overview", label: "Overview",   icon: BarChart3 },
            { id: "exams",    label: "Exams",      icon: BookOpen  },
            { id: "items",    label: "Item Bank",  icon: TrendingUp },
            { id: "flags",    label: "Flags",      icon: Shield    },
          ].map((item) => (
            <button key={item.id} onClick={() => setTab(item.id as ActiveTab)}
              className={cn(
                "w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm mb-1 transition-all",
                tab === item.id
                  ? "bg-blue-600 text-white font-medium"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              )}>
              <item.icon className="w-4 h-4" />
              {item.label}
              {item.id === "flags" && (overview?.flagged_for_collusion || 0) > 0 && (
                <span className="ml-auto bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                  {overview?.flagged_for_collusion}
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="p-3 border-t border-gray-800">
          <button onClick={logout}
            className="w-full flex items-center gap-2 px-3 py-2.5 text-sm text-gray-500 hover:text-red-400 rounded-lg hover:bg-red-500/10 transition-all">
            <LogOut className="w-4 h-4" /> Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="ml-56 flex-1 p-6">

        {/* ── OVERVIEW TAB ── */}
        {tab === "overview" && (
          <div className="animate-fade-in">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-bold text-white">Platform Overview</h1>
                <p className="text-gray-400 text-sm mt-0.5">Real-time metrics across all exams</p>
              </div>
              <button onClick={loadData} className="btn-secondary flex items-center gap-2 py-2 px-3 text-sm">
                <RefreshCw className="w-3.5 h-3.5" /> Refresh
              </button>
            </div>

            {/* KPI cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
              {[
                { label: "Total Students",      value: overview?.total_students || 0,        color: "text-blue-400",    icon: Users },
                { label: "Question Items",      value: overview?.total_items || 0,           color: "text-purple-400",  icon: BookOpen },
                { label: "Total Sessions",      value: overview?.total_exam_sessions || 0,   color: "text-white",       icon: TrendingUp },
                { label: "Completed",           value: overview?.completed_sessions || 0,    color: "text-emerald-400", icon: CheckCircle2 },
                { label: "Flagged",             value: overview?.flagged_for_collusion || 0, color: "text-red-400",     icon: AlertTriangle },
                { label: "Avg Ability (θ)",     value: (overview?.avg_theta_all_students || 0).toFixed(3), color: "text-cyan-400", icon: BarChart3 },
              ].map((kpi) => (
                <div key={kpi.label} className="stat-card">
                  <div className="flex items-center gap-1.5 text-gray-500 text-xs mb-2">
                    <kpi.icon className="w-3.5 h-3.5" />
                    <span>{kpi.label}</span>
                  </div>
                  <div className={cn("text-2xl font-bold mono", kpi.color)}>{kpi.value}</div>
                </div>
              ))}
            </div>

            {/* Per-exam stats */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              {/* Exam selector */}
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-white">Exam Analytics</h3>
                  <select
                    value={selectedExam || ""}
                    onChange={(e) => setSelectedExam(e.target.value)}
                    className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    {exams.map(e => (
                      <option key={e.exam_id} value={e.exam_id}>{e.title}</option>
                    ))}
                  </select>
                </div>

                {examStats ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { label: "Attempts",     value: examStats.total_attempts },
                        { label: "Completed",    value: examStats.completed_attempts },
                        { label: "Avg θ",        value: examStats.avg_theta.toFixed(3) },
                      ].map(s => (
                        <div key={s.label} className="bg-gray-800/50 rounded-lg p-3 text-center">
                          <div className="text-lg font-bold mono text-white">{s.value}</div>
                          <div className="text-xs text-gray-500">{s.label}</div>
                        </div>
                      ))}
                    </div>

                    {examStats.flagged_for_collusion > 0 && (
                      <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                        <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                        <span className="text-sm text-red-300">
                          {examStats.flagged_for_collusion} session(s) flagged for collusion
                        </span>
                        <button onClick={() => setTab("flags")} className="ml-auto text-xs text-red-400 underline">View</button>
                      </div>
                    )}

                    <div className="text-xs text-gray-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Avg items administered: {examStats.avg_items_administered.toFixed(1)} (vs {exams.find(e=>e.exam_id===selectedExam)?.max_items} max)
                    </div>
                  </div>
                ) : (
                  <p className="text-gray-600 text-sm text-center py-4">No sessions yet for this exam</p>
                )}
              </div>

              {/* Grade distribution */}
              <div className="card">
                <h3 className="font-semibold text-white mb-4">Grade Distribution</h3>
                {gradeChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart data={gradeChartData} barSize={28}>
                      <XAxis dataKey="grade" tick={{ fill: "#6b7280", fontSize: 12 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip
                        contentStyle={{ background: "#1f2937", border: "1px solid #374151", borderRadius: "8px" }}
                        labelStyle={{ color: "#f9fafb" }}
                        itemStyle={{ color: "#60a5fa" }}
                      />
                      <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-44 flex items-center justify-center text-gray-600 text-sm">
                    No grade data yet — run an exam first
                  </div>
                )}
              </div>
            </div>

            {/* Ability distribution */}
            {thetaHistData.length > 0 && (
              <div className="card">
                <h3 className="font-semibold text-white mb-4">
                  Student Ability Distribution (θ)
                  <span className="text-xs text-gray-500 font-normal ml-2">IRT latent trait scale</span>
                </h3>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={thetaHistData} barSize={20}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis dataKey="range" tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ background: "#1f2937", border: "1px solid #374151", borderRadius: "8px" }} />
                    <Bar dataKey="count" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}

        {/* ── EXAMS TAB ── */}
        {tab === "exams" && (
          <div className="animate-fade-in">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-bold text-white">Exam Management</h1>
                <p className="text-gray-400 text-sm">Create, publish, and monitor exams</p>
              </div>
              <Link href="/admin/create-exam" className="btn-primary flex items-center gap-2 py-2">
                <Plus className="w-4 h-4" /> New Exam
              </Link>
            </div>

            <div className="space-y-3">
              {exams.length === 0 ? (
                <div className="card text-center py-16 text-gray-500">
                  <BookOpen className="w-10 h-10 mx-auto mb-3 opacity-30" />
                  <p>No exams yet. Create your first exam!</p>
                  <Link href="/admin/create-exam" className="btn-primary inline-flex items-center gap-2 mt-4 py-2">
                    <Plus className="w-4 h-4" /> Create Exam
                  </Link>
                </div>
              ) : exams.map((exam) => (
                <div key={exam.exam_id} className="card flex items-center gap-4 p-5">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-white">{exam.title}</h3>
                      <span className={cn("badge", exam.status === "active" ? "badge-green" : exam.status === "closed" ? "badge-gray" : "badge-yellow")}>
                        {exam.status}
                      </span>
                      {exam.is_adaptive && <span className="badge badge-purple">Adaptive</span>}
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>Subject: <span className="text-gray-300">{exam.subject}</span></span>
                      <span>Max items: <span className="text-gray-300">{exam.max_items}</span></span>
                      <span>Time: <span className="text-gray-300">{exam.time_limit_minutes} min</span></span>
                      <span>{formatDate(exam.created_at)}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button onClick={() => { setSelectedExam(exam.exam_id); setTab("overview") }}
                      className="btn-secondary py-1.5 px-3 text-xs flex items-center gap-1.5">
                      <Eye className="w-3 h-3" /> Stats
                    </button>
                    {exam.status === "draft" && (
                      <button onClick={() => publishExam(exam.exam_id)}
                        className="btn-success py-1.5 px-3 text-xs flex items-center gap-1.5">
                        <CheckCircle2 className="w-3 h-3" /> Publish
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── ITEM BANK TAB ── */}
        {tab === "items" && <ItemBankTab />}

        {/* ── FLAGS TAB ── */}
        {tab === "flags" && <FlagsTab exams={exams} />}

      </main>
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────

function ItemBankTab() {
  const [items, setItems] = useState<{ item_id: string; subject: string; topic: string; content: string; irt_b: number; irt_calibrated: boolean }[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")

  useEffect(() => { load() }, [])

  async function load() {
    try {
      const { itemsApi } = await import("@/lib/api")
      const data = await itemsApi.list()
      setItems(data.items as typeof items)
    } catch { toast.error("Failed to load items") }
    finally { setLoading(false) }
  }

  const filtered = items.filter(i =>
    i.content.toLowerCase().includes(search.toLowerCase()) ||
    i.subject.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Item Bank</h1>
          <p className="text-gray-400 text-sm">{items.length} questions · IRT-calibrated</p>
        </div>
        <Link href="/admin/create-item" className="btn-primary flex items-center gap-2 py-2">
          <Plus className="w-4 h-4" /> Add Item
        </Link>
      </div>

      <input value={search} onChange={e => setSearch(e.target.value)}
        placeholder="Search questions..." className="input mb-4" />

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-7 h-7 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((item) => (
            <div key={item.item_id} className="card p-4 flex gap-4 items-start">
              <div className="flex-1">
                <p className="text-gray-200 text-sm leading-relaxed">{item.content.slice(0, 120)}{item.content.length > 120 ? "…" : ""}</p>
                <div className="flex items-center gap-3 mt-2">
                  <span className="badge badge-blue">{item.subject}</span>
                  <span className="text-xs text-gray-600 mono">b = {item.irt_b.toFixed(2)}</span>
                  {item.irt_calibrated && <span className="badge badge-green">Calibrated</span>}
                </div>
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="text-center py-12 text-gray-600">No items match your search</div>
          )}
        </div>
      )}
    </div>
  )
}

function FlagsTab({ exams }: { exams: Exam[] }) {
  const [selectedExam, setSelectedExam] = useState(exams[0]?.exam_id || "")
  const [flags, setFlags] = useState<{ student_name: string; student_email: string; collusion_probability: number; grade: string; session_id: string }[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => { if (selectedExam) load() }, [selectedExam])

  async function load() {
    setLoading(true)
    try {
      const data = await analyticsApi.flaggedSessions(selectedExam)
      setFlags(data.flagged_sessions || [])
    } catch { setFlags([]) }
    finally { setLoading(false) }
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Shield className="w-6 h-6 text-red-400" /> Academic Integrity Flags
          </h1>
          <p className="text-gray-400 text-sm">GNN + SBERT collusion detection results</p>
        </div>
        <select value={selectedExam} onChange={e => setSelectedExam(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none">
          {exams.map(e => <option key={e.exam_id} value={e.exam_id}>{e.title}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-7 h-7 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : flags.length === 0 ? (
        <div className="card text-center py-16">
          <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
          <p className="text-white font-medium">No flags detected</p>
          <p className="text-gray-500 text-sm mt-1">All sessions passed GNN collusion analysis</p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-3 mb-4">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
            <p className="text-sm text-red-300">
              {flags.length} session(s) flagged. These require human review before final grading.
            </p>
          </div>

          {flags.map((f, i) => (
            <div key={i} className="card flex items-center gap-4 p-5 border-red-900/30">
              <div className="w-10 h-10 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-4 h-4 text-red-400" />
              </div>
              <div className="flex-1">
                <p className="text-white font-medium">{f.student_name}</p>
                <p className="text-gray-500 text-xs">{f.student_email}</p>
              </div>
              <div className="text-right shrink-0">
                <div className="text-lg font-bold text-red-400 mono">{(f.collusion_probability * 100).toFixed(1)}%</div>
                <div className="text-xs text-gray-500">Collusion probability</div>
              </div>
              <div className={cn("badge border ml-2", gradeBg(f.grade || "F"))}>{f.grade || "F"}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// Helper: build histogram from theta values
function buildHistogram(thetas: number[]) {
  const bins = [
    { range: "< -2", min: -Infinity, max: -2 },
    { range: "-2 to -1", min: -2, max: -1 },
    { range: "-1 to 0", min: -1, max: 0 },
    { range: "0 to 1", min: 0, max: 1 },
    { range: "1 to 2", min: 1, max: 2 },
    { range: "> 2", min: 2, max: Infinity },
  ]
  return bins.map(b => ({
    range: b.range,
    count: thetas.filter(t => t >= b.min && t < b.max).length,
  }))
}

function LoadingScreen() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-center">
        <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-gray-400">Loading admin panel...</p>
      </div>
    </div>
  )
}