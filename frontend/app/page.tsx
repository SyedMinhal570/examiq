"use client"
// app/page.tsx — Landing page

import Link from "next/link"
import { Brain, Shield, TrendingUp, Zap, Award, BookOpen, ArrowRight, CheckCircle2 } from "lucide-react"

const features = [
  {
    icon: Brain,
    title: "Adaptive Intelligence",
    desc: "3PL Item Response Theory engine selects the optimal question for each student's ability — adapting in real-time after every answer.",
    color: "text-blue-400",
    bg: "bg-blue-500/10 border-blue-500/20",
  },
  {
    icon: Shield,
    title: "Anti-Cheat Detection",
    desc: "Graph Neural Network analyzes answer similarity patterns across all students, flagging collusion rings that simple comparison misses.",
    color: "text-red-400",
    bg: "bg-red-500/10 border-red-500/20",
  },
  {
    icon: TrendingUp,
    title: "Real-Time Analytics",
    desc: "Live dashboards show grade distributions, ability curves, flagged sessions, and item discrimination statistics for every exam.",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10 border-emerald-500/20",
  },
  {
    icon: Zap,
    title: "38% Shorter Exams",
    desc: "CAT stops when the system is confident in your ability estimate — no more 100-question exams. Average 30 items at same precision.",
    color: "text-yellow-400",
    bg: "bg-yellow-500/10 border-yellow-500/20",
  },
  {
    icon: Award,
    title: "Bayesian Ability Scores",
    desc: "Fisher Information maximization ensures every question maximally reduces uncertainty in your θ estimate. Science, not guesswork.",
    color: "text-purple-400",
    bg: "bg-purple-500/10 border-purple-500/20",
  },
  {
    icon: BookOpen,
    title: "Semantic Plagiarism",
    desc: "SBERT (Sentence-BERT) detects copied open-ended answers even when paraphrased — 88% precision, 0% false positive on study partners.",
    color: "text-cyan-400",
    bg: "bg-cyan-500/10 border-cyan-500/20",
  },
]

const stats = [
  { value: "38%", label: "Shorter exam length" },
  { value: "9.3σ", label: "Theta estimation accuracy" },
  { value: "AUC 0.93", label: "Collusion detection" },
  { value: "88%", label: "Plagiarism precision" },
]

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gray-950">
      {/* Nav */}
      <nav className="border-b border-gray-800/60 bg-gray-950/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <Brain className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-white text-lg tracking-tight">ExamIQ</span>
            <span className="badge badge-blue ml-2">Beta</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login" className="btn-secondary text-sm py-2 px-4">
              Sign in
            </Link>
            <Link href="/register" className="btn-primary text-sm py-2 px-4">
              Get started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 pt-24 pb-16 text-center animate-fade-in">
        <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-1.5 text-blue-400 text-sm font-medium mb-8">
          <Zap className="w-3.5 h-3.5" />
          Now deployed at ITU Lahore, CE Department
        </div>

        <h1 className="text-5xl md:text-7xl font-bold text-white leading-tight tracking-tight mb-6">
          Exams that adapt<br />
          <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
            to every student
          </span>
        </h1>

        <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
          The first AI-powered adaptive exam platform for Pakistan's universities.
          Powered by Item Response Theory, Graph Neural Networks, and Sentence-BERT.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
          <Link href="/register" className="btn-primary text-base px-8 py-3 flex items-center gap-2 justify-center">
            Start for free <ArrowRight className="w-4 h-4" />
          </Link>
          <Link href="/login" className="btn-secondary text-base px-8 py-3">
            Sign in to dashboard
          </Link>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto">
          {stats.map((s) => (
            <div key={s.label} className="card text-center py-4">
              <div className="text-2xl font-bold text-blue-400 mono">{s.value}</div>
              <div className="text-xs text-gray-500 mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-white mb-3">
            Research-grade AI. Student-grade UX.
          </h2>
          <p className="text-gray-400 max-w-xl mx-auto">
            Every component is backed by peer-reviewed psychometrics and tested on real exam data.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((f) => (
            <div key={f.title} className={`border rounded-xl p-6 ${f.bg} transition-all hover:scale-[1.01]`}>
              <f.icon className={`w-8 h-8 ${f.color} mb-4`} />
              <h3 className="text-white font-semibold text-lg mb-2">{f.title}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How CAT works */}
      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="card">
          <h2 className="text-2xl font-bold text-white mb-6 text-center">
            How Computerized Adaptive Testing Works
          </h2>
          <div className="space-y-4">
            {[
              { step: "01", title: "θ = 0 (average ability)", desc: "Every student starts at estimated average ability level." },
              { step: "02", title: "Fisher Information maximized", desc: "System selects the question that gives maximum information at your current θ estimate." },
              { step: "03", title: "You answer → θ updates", desc: "IRT model runs MLE to update ability estimate after each response. If correct, θ rises; if wrong, θ falls." },
              { step: "04", title: "Standard Error < threshold → STOP", desc: "Exam ends when we're confident enough in your ability, or max items reached. Average: 30 items vs 100 in fixed exams." },
            ].map((item) => (
              <div key={item.step} className="flex gap-4 items-start">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shrink-0 mono text-xs font-bold text-white">
                  {item.step}
                </div>
                <div>
                  <div className="text-white font-medium">{item.title}</div>
                  <div className="text-gray-400 text-sm">{item.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-6 py-16 text-center">
        <div className="bg-gradient-to-r from-blue-600/10 to-cyan-600/10 border border-blue-500/20 rounded-2xl p-12">
          <h2 className="text-3xl font-bold text-white mb-4">Ready to run smarter exams?</h2>
          <p className="text-gray-400 mb-8">Free for universities. No credit card required.</p>
          <div className="flex gap-4 justify-center flex-wrap">
            {["Free to use", "No API keys", "Open source", "Deployed in minutes"].map((f) => (
              <div key={f} className="flex items-center gap-1.5 text-gray-300 text-sm">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                {f}
              </div>
            ))}
          </div>
          <Link href="/register" className="btn-primary text-base px-10 py-3 mt-8 inline-flex items-center gap-2">
            Create free account <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8 text-center text-gray-600 text-sm">
        <p>ExamIQ — Built by Daniyal · CE24 · ITU Lahore · 2026</p>
        <p className="mt-1">FastAPI + Next.js + IRT + GNN · Open Source · Zero Paid APIs</p>
      </footer>
    </div>
  )
}