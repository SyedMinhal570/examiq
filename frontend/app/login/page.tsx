"use client"
// app/login/page.tsx

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Brain, Eye, EyeOff, Loader2 } from "lucide-react"
import toast from "react-hot-toast"
import Cookies from "js-cookie"
import { authApi } from "@/lib/api"
import { useAuthStore } from "@/lib/store"

export default function LoginPage() {
  const router = useRouter()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      const data = await authApi.login(email, password)
      Cookies.set("examiq_token", data.access_token, { expires: 1 })
      setAuth(
        { user_id: data.user_id, email: data.email, full_name: data.full_name, role: data.role as "student" | "faculty" | "admin", is_active: true },
        data.access_token
      )
      toast.success(`Welcome back, ${data.full_name.split(" ")[0]}!`)
      router.push(data.role === "student" ? "/dashboard" : "/admin")
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Login failed"
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-slide-up">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-600 rounded-xl mb-4">
            <Brain className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Welcome back</h1>
          <p className="text-gray-400 mt-1">Sign in to ExamIQ</p>
        </div>

        <div className="card">
          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Email</label>
              <input
                type="email" required
                value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="you@itu.edu.pk"
                className="input"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Password</label>
              <div className="relative">
                <input
                  type={showPw ? "text" : "password"} required
                  value={password} onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input pr-10"
                />
                <button type="button" onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full py-3 flex items-center justify-center gap-2">
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          {/* Demo credentials */}
          <div className="mt-5 p-3 bg-gray-800/50 rounded-lg border border-gray-700/50">
            <p className="text-xs text-gray-400 font-medium mb-2">Demo credentials</p>
            <div className="space-y-1 mono text-xs">
              <div className="flex justify-between"><span className="text-gray-500">Student:</span><span className="text-gray-300">student@itu.edu.pk / Student@123</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Faculty:</span><span className="text-gray-300">faculty@itu.edu.pk / Faculty@123</span></div>
            </div>
          </div>
        </div>

        <p className="text-center text-gray-500 text-sm mt-5">
          No account?{" "}
          <Link href="/register" className="text-blue-400 hover:text-blue-300 font-medium">
            Create one free
          </Link>
        </p>
      </div>
    </div>
  )
}
