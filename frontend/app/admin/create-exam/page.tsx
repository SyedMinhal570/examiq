"use client"
// app/admin/create-exam/page.tsx

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { ArrowLeft, Brain, BookOpen, Clock, Hash, Zap, Loader2 } from "lucide-react"
import toast from "react-hot-toast"
import { analyticsApi } from "@/lib/api"

export default function CreateExamPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    title: "",
    subject: "",
    max_items: 30,
    time_limit_minutes: 60,
    is_adaptive: true,
  })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.title.trim() || !form.subject.trim()) {
      toast.error("Title and subject are required"); return
    }
    setLoading(true)
    try {
      const data = await analyticsApi.createExam(form)
      toast.success("Exam created! Add items then publish.")
      router.push("/admin")
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to create exam"
      toast.error(msg)
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-gray-950 p-6">
      <div className="max-w-2xl mx-auto animate-slide-up">
        <Link href="/admin" className="flex items-center gap-2 text-gray-400 hover:text-white mb-6 text-sm transition-colors w-fit">
          <ArrowLeft className="w-4 h-4" /> Back to Admin
        </Link>

        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Create New Exam</h1>
            <p className="text-gray-400 text-sm">Configure adaptive exam settings</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Title */}
          <div className="card">
            <label className="block text-sm font-medium text-gray-300 mb-1.5 flex items-center gap-2">
              <BookOpen className="w-3.5 h-3.5 text-blue-400" /> Exam Title
            </label>
            <input value={form.title}
              onChange={e => setForm({ ...form, title: e.target.value })}
              placeholder="e.g. Computer Architecture Mid-Term CE24"
              className="input" required />
          </div>

          {/* Subject */}
          <div className="card">
            <label className="block text-sm font-medium text-gray-300 mb-1.5 flex items-center gap-2">
              <Hash className="w-3.5 h-3.5 text-purple-400" /> Subject Code
            </label>
            <input value={form.subject}
              onChange={e => setForm({ ...form, subject: e.target.value })}
              placeholder="e.g. COA, DSA, OS, CN"
              className="input" required />
            <p className="text-xs text-gray-600 mt-1.5">
              Items with this subject tag will be pulled from the item bank
            </p>
          </div>

          {/* Settings grid */}
          <div className="card">
            <h3 className="text-sm font-medium text-gray-300 mb-4">Exam Settings</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1.5 flex items-center gap-1">
                  <Hash className="w-3 h-3" /> Max Items (CAT will stop earlier if confident)
                </label>
                <input type="number" min={5} max={100}
                  value={form.max_items}
                  onChange={e => setForm({ ...form, max_items: parseInt(e.target.value) })}
                  className="input" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1.5 flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Time Limit (minutes)
                </label>
                <input type="number" min={10} max={360}
                  value={form.time_limit_minutes}
                  onChange={e => setForm({ ...form, time_limit_minutes: parseInt(e.target.value) })}
                  className="input" />
              </div>
            </div>
          </div>

          {/* Adaptive toggle */}
          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2 text-white font-medium">
                  <Zap className="w-4 h-4 text-yellow-400" /> Adaptive Testing (CAT)
                </div>
                <p className="text-xs text-gray-500 mt-0.5">
                  Uses IRT to select optimal questions. Reduces exam length by ~38%.
                </p>
              </div>
              <button type="button" onClick={() => setForm({ ...form, is_adaptive: !form.is_adaptive })}
                className={`w-11 h-6 rounded-full transition-all relative ${form.is_adaptive ? "bg-blue-600" : "bg-gray-700"}`}>
                <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${form.is_adaptive ? "translate-x-5" : ""}`} />
              </button>
            </div>
          </div>

          {/* Info box */}
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4 text-sm text-blue-300">
            <p className="font-medium mb-1">After creating:</p>
            <ol className="list-decimal list-inside space-y-0.5 text-blue-300/80 text-xs">
              <li>Add questions to the item bank (Items tab) with matching subject</li>
              <li>Click "Publish" to make it available to students</li>
              <li>Students take the exam — CAT engine adapts to each</li>
              <li>View results and collusion flags in Overview</li>
            </ol>
          </div>

          <button type="submit" disabled={loading}
            className="btn-primary w-full py-3.5 flex items-center justify-center gap-2 text-base">
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {loading ? "Creating..." : "Create Exam"}
          </button>
        </form>
      </div>
    </div>
  )
}