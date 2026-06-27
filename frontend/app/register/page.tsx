"use client"
// app/register/page.tsx

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Brain, Loader2 } from "lucide-react"
import toast from "react-hot-toast"
import Cookies from "js-cookie"
import { authApi } from "@/lib/api"
import { useAuthStore } from "@/lib/store"

export default function RegisterPage() {
  const router = useRouter()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [form, setForm] = useState({ full_name: "", email: "", password: "", role: "student" })
  const [loading, setLoading] = useState(false)

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      const data = await authApi.register(form)
      Cookies.set("examiq_token", data.access_token, { expires: 1 })
      setAuth(
        { user_id: data.user_id, email: data.email, full_name: data.full_name, role: data.role as "student"|"faculty"|"admin", is_active: true },
        data.access_token
      )
      toast.success("Account created! Welcome to ExamIQ 🎉")
      router.push(data.role === "student" ? "/dashboard" : "/admin")
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Registration failed"
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-slide-up">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-600 rounded-xl mb-4">
            <Brain className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Create account</h1>
          <p className="text-gray-400 mt-1">Free for students and faculty</p>
        </div>

        <div className="card">
          <form onSubmit={handleRegister} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Full name</label>
              <input type="text" required value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                placeholder="Syed Muhammad Daniyal" className="input" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Email</label>
              <input type="email" required value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="you@itu.edu.pk" className="input" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Password</label>
              <input type="password" required value={form.password} minLength={8}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Min 8 chars, 1 uppercase, 1 number" className="input" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">I am a</label>
              <div className="grid grid-cols-2 gap-3">
                {(["student", "faculty"] as const).map((role) => (
                  <button key={role} type="button"
                    onClick={() => setForm({ ...form, role })}
                    className={`py-2.5 rounded-lg border text-sm font-medium capitalize transition-all
                      ${form.role === role
                        ? "bg-blue-600 border-blue-500 text-white"
                        : "bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600"
                      }`}>
                    {role}
                  </button>
                ))}
              </div>
            </div>
            <button type="submit" disabled={loading}
              className="btn-primary w-full py-3 flex items-center justify-center gap-2">
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? "Creating account..." : "Create account"}
            </button>
          </form>
        </div>

        <p className="text-center text-gray-500 text-sm mt-5">
          Already have an account?{" "}
          <Link href="/login" className="text-blue-400 hover:text-blue-300 font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}