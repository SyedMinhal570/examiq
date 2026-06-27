// lib/api.ts — Axios client with auto JWT injection + error handling

import axios, { AxiosError } from "axios"
import Cookies from "js-cookie"
import type {
  TokenResponse, User, Exam, ExamItem,
  StartExamResponse, NextQuestionResponse,
  SubmitAnswerResponse, ExamResult,
  AnalyticsOverview, ExamStats,
} from "@/types"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
})

// ── Request interceptor: attach JWT automatically ─────────────────
api.interceptors.request.use((config) => {
  const token = Cookies.get("examiq_token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: redirect to login on 401 ───────────────
api.interceptors.response.use(
  (res) => res,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      Cookies.remove("examiq_token")
      Cookies.remove("examiq_user")
      if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
        window.location.href = "/login"
      }
    }
    return Promise.reject(error)
  }
)

// ── Auth ──────────────────────────────────────────────────────────
export const authApi = {
  register: async (data: {
    email: string
    password: string
    full_name: string
    role: string
  }): Promise<TokenResponse> => {
    const res = await api.post("/auth/register", data)
    return res.data
  },

  login: async (email: string, password: string): Promise<TokenResponse> => {
    const res = await api.post("/auth/login", { email, password })
    return res.data
  },

  me: async (): Promise<User> => {
    const res = await api.get("/auth/me")
    return res.data
  },
}

// ── Exams ─────────────────────────────────────────────────────────
export const examApi = {
  listExams: async (): Promise<{ exams: Exam[] }> => {
    const res = await api.get("/analytics/exams")
    return res.data
  },

  startExam: async (exam_id: string): Promise<StartExamResponse> => {
    const res = await api.post("/exam/start", { exam_id })
    return res.data
  },

  getNextQuestion: async (session_id: string): Promise<NextQuestionResponse> => {
    const res = await api.get(`/exam/session/${session_id}/next`)
    return res.data
  },

  submitAnswer: async (
    session_id: string,
    data: {
      item_id: string
      selected_option?: number | null
      open_answer?: string | null
      time_taken_seconds: number
    }
  ): Promise<SubmitAnswerResponse> => {
    const res = await api.post(`/exam/session/${session_id}/answer`, data)
    return res.data
  },

  finishExam: async (session_id: string): Promise<Record<string, unknown>> => {
    const res = await api.post(`/exam/session/${session_id}/finish`)
    return res.data
  },

  getResult: async (session_id: string): Promise<ExamResult> => {
    const res = await api.get(`/exam/session/${session_id}/result`)
    return res.data
  },

  getMySessions: async (): Promise<{ sessions: ExamResult[] }> => {
    const res = await api.get("/exam/my-sessions")
    return res.data
  },
}

// ── Items ─────────────────────────────────────────────────────────
export const itemsApi = {
  list: async (subject?: string): Promise<{ items: ExamItem[]; total: number }> => {
    const res = await api.get("/items/", { params: { subject, limit: 200 } })
    return res.data
  },

  create: async (data: Partial<ExamItem> & { irt_a?: number; irt_b?: number; irt_c?: number }): Promise<ExamItem> => {
    const res = await api.post("/items/", data)
    return res.data
  },

  bulkCreate: async (items: unknown[]): Promise<{ created: number; item_ids: string[] }> => {
    const res = await api.post("/items/bulk", items)
    return res.data
  },

  delete: async (item_id: string): Promise<void> => {
    await api.delete(`/items/${item_id}`)
  },
}

// ── Analytics ─────────────────────────────────────────────────────
export const analyticsApi = {
  overview: async (): Promise<AnalyticsOverview> => {
    const res = await api.get("/analytics/overview")
    return res.data
  },

  examStats: async (exam_id: string): Promise<ExamStats> => {
    const res = await api.get(`/analytics/exam/${exam_id}`)
    return res.data
  },

  flaggedSessions: async (exam_id: string) => {
    const res = await api.get(`/analytics/exam/${exam_id}/flags`)
    return res.data
  },

  createExam: async (data: {
    title: string
    subject: string
    max_items: number
    time_limit_minutes: number
    is_adaptive: boolean
  }) => {
    const res = await api.post("/analytics/exams", data)
    return res.data
  },

  publishExam: async (exam_id: string) => {
    const res = await api.put(`/analytics/exams/${exam_id}/publish`)
    return res.data
  },
}

// ── Health ────────────────────────────────────────────────────────
export const healthApi = {
  check: async () => {
    const res = await api.get("/health/ready", { baseURL: "http://localhost:8000" })
    return res.data
  },
}

export default api