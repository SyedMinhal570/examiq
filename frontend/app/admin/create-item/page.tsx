"use client"
// app/admin/create-item/page.tsx

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { ArrowLeft, Plus, Trash2, Brain, Loader2, Info } from "lucide-react"
import toast from "react-hot-toast"
import { itemsApi } from "@/lib/api"
import { cn } from "@/lib/utils"

export default function CreateItemPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [itemType, setItemType] = useState<"mcq" | "open">("mcq")
  const [form, setForm] = useState({
    subject: "",
    topic: "",
    content: "",
    options: ["", "", "", ""],
    correct_option: 0,
    irt_a: 1.0,
    irt_b: 0.0,
    irt_c: 0.25,
  })

  function updateOption(idx: number, val: string) {
    const opts = [...form.options]
    opts[idx] = val
    setForm({ ...form, options: opts })
  }

  function addOption() {
    if (form.options.length >= 6) return
    setForm({ ...form, options: [...form.options, ""] })
  }

  function removeOption(idx: number) {
    if (form.options.length <= 2) return
    const opts = form.options.filter((_, i) => i !== idx)
    setForm({ ...form, options: opts, correct_option: Math.min(form.correct_option, opts.length - 1) })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.subject || !form.content) { toast.error("Subject and question are required"); return }
    if (itemType === "mcq") {
      if (form.options.some(o => !o.trim())) { toast.error("Fill in all options"); return }
    }

    setLoading(true)
    try {
      await itemsApi.create({
        subject: form.subject,
        topic: form.topic,
        content: form.content,
        item_type: itemType,
        options: itemType === "mcq" ? form.options : undefined,
        correct_option: itemType === "mcq" ? form.correct_option : undefined,
        irt_a: form.irt_a,
        irt_b: form.irt_b,
        irt_c: form.irt_c,
      })
      toast.success("Item added to bank!")
      router.push("/admin")
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to create item"
      toast.error(msg)
    } finally { setLoading(false) }
  }

  const difficultyLabel = form.irt_b < -1 ? "Easy" : form.irt_b < 1 ? "Medium" : "Hard"
  const difficultyColor = form.irt_b < -1 ? "text-emerald-400" : form.irt_b < 1 ? "text-yellow-400" : "text-red-400"

  return (
    <div className="min-h-screen bg-gray-950 p-6">
      <div className="max-w-2xl mx-auto animate-slide-up">
        <Link href="/admin" className="flex items-center gap-2 text-gray-400 hover:text-white mb-6 text-sm transition-colors w-fit">
          <ArrowLeft className="w-4 h-4" /> Back to Admin
        </Link>

        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-purple-600 rounded-xl flex items-center justify-center">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Add Exam Item</h1>
            <p className="text-gray-400 text-sm">Add a question to the IRT item bank</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">

          {/* Type selector */}
          <div className="card">
            <label className="block text-sm font-medium text-gray-300 mb-3">Question Type</label>
            <div className="grid grid-cols-2 gap-3">
              {[
                { id: "mcq",  label: "Multiple Choice", desc: "Auto-graded, IRT-ready" },
                { id: "open", label: "Open Ended",      desc: "SBERT plagiarism detection" },
              ].map(t => (
                <button key={t.id} type="button" onClick={() => setItemType(t.id as "mcq" | "open")}
                  className={cn("p-3 rounded-lg border text-left transition-all",
                    itemType === t.id ? "bg-blue-600/15 border-blue-500 text-white" : "bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600")}>
                  <div className="font-medium text-sm">{t.label}</div>
                  <div className="text-xs opacity-60 mt-0.5">{t.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Subject + Topic */}
          <div className="card">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Subject *</label>
                <input value={form.subject} onChange={e => setForm({ ...form, subject: e.target.value })}
                  placeholder="COA, DSA, OS, CN…" className="input" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Topic</label>
                <input value={form.topic} onChange={e => setForm({ ...form, topic: e.target.value })}
                  placeholder="e.g. Pipeline Hazards" className="input" />
              </div>
            </div>
          </div>

          {/* Question */}
          <div className="card">
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Question *</label>
            <textarea value={form.content} onChange={e => setForm({ ...form, content: e.target.value })}
              placeholder="Write the question here..."
              className="input min-h-24 resize-none" required />
          </div>

          {/* MCQ Options */}
          {itemType === "mcq" && (
            <div className="card">
              <label className="block text-sm font-medium text-gray-300 mb-3">Answer Options *</label>
              <div className="space-y-2.5">
                {form.options.map((opt, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <button type="button" onClick={() => setForm({ ...form, correct_option: i })}
                      className={cn("w-7 h-7 rounded-full border flex items-center justify-center text-xs font-bold shrink-0 transition-all",
                        form.correct_option === i
                          ? "bg-emerald-600 border-emerald-500 text-white"
                          : "border-gray-600 text-gray-500 hover:border-gray-500")}>
                      {["A","B","C","D","E","F"][i]}
                    </button>
                    <input value={opt} onChange={e => updateOption(i, e.target.value)}
                      placeholder={`Option ${["A","B","C","D","E","F"][i]}`}
                      className="input flex-1" />
                    {form.options.length > 2 && (
                      <button type="button" onClick={() => removeOption(i)}
                        className="text-gray-600 hover:text-red-400 transition-colors">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between mt-3">
                <p className="text-xs text-gray-500">
                  Click a letter to mark correct answer
                  {form.correct_option !== null && (
                    <span className="text-emerald-400 ml-1">
                      · Correct: {["A","B","C","D","E","F"][form.correct_option]}
                    </span>
                  )}
                </p>
                {form.options.length < 6 && (
                  <button type="button" onClick={addOption}
                    className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">
                    <Plus className="w-3 h-3" /> Add option
                  </button>
                )}
              </div>
            </div>
          )}

          {/* IRT Parameters */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <h3 className="text-sm font-medium text-gray-300">IRT Parameters</h3>
              <div className="group relative">
                <Info className="w-3.5 h-3.5 text-gray-600 cursor-help" />
                <div className="absolute bottom-5 left-0 hidden group-hover:block bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs text-gray-300 w-64 z-10 shadow-xl">
                  <p><strong>a</strong> = Discrimination (0.5–2.5): how well this question separates ability levels</p>
                  <p className="mt-1"><strong>b</strong> = Difficulty (-3 to +3): ability level needed to have 50% chance of correct</p>
                  <p className="mt-1"><strong>c</strong> = Guessing (0–0.35): probability of correct by random guessing</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1.5">
                  a (Discrimination)
                </label>
                <input type="number" step={0.1} min={0.1} max={3.0}
                  value={form.irt_a} onChange={e => setForm({ ...form, irt_a: parseFloat(e.target.value) })}
                  className="input" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1.5">
                  b (Difficulty) → <span className={difficultyColor}>{difficultyLabel}</span>
                </label>
                <input type="range" min={-4} max={4} step={0.1}
                  value={form.irt_b} onChange={e => setForm({ ...form, irt_b: parseFloat(e.target.value) })}
                  className="w-full accent-blue-500" />
                <div className="text-center text-blue-400 text-xs mono mt-1">{form.irt_b.toFixed(1)}</div>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1.5">
                  c (Guessing)
                </label>
                <input type="number" step={0.05} min={0} max={0.5}
                  value={form.irt_c} onChange={e => setForm({ ...form, irt_c: parseFloat(e.target.value) })}
                  className="input" />
              </div>
            </div>
            <p className="text-xs text-gray-600 mt-3">
              💡 Tip: Leave defaults for now. After 30+ students take the exam, run calibration to auto-estimate accurate IRT parameters.
            </p>
          </div>

          <button type="submit" disabled={loading}
            className="btn-primary w-full py-3.5 flex items-center justify-center gap-2 text-base">
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {loading ? "Adding to bank..." : "Add to Item Bank"}
          </button>
        </form>
      </div>
    </div>
  )
}