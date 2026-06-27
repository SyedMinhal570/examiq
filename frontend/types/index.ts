// types/index.ts — All TypeScript interfaces matching backend schemas

export interface User {
  user_id: string
  email: string
  full_name: string
  role: "student" | "faculty" | "admin"
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user_id: string
  email: string
  full_name: string
  role: string
}

export interface ExamItem {
  item_id: string
  subject: string
  topic: string
  content: string
  item_type: "mcq" | "open"
  options: string[] | null
  correct_option: number | null
  irt_b: number
  irt_calibrated: boolean
}

export interface Exam {
  exam_id: string
  title: string
  subject: string
  status: "draft" | "active" | "closed"
  is_adaptive: boolean
  max_items: number
  time_limit_minutes: number
  created_at: string
}

export interface StartExamResponse {
  session_id: string
  exam_id: string
  exam_title: string
  max_items: number
  time_limit_minutes: number
  message: string
}

export interface NextQuestionResponse {
  item_id: string
  content: string
  item_type: "mcq" | "open"
  options: string[] | null
  question_number: number
  theta_estimate: number
  session_complete: boolean
}

export interface SubmitAnswerResponse {
  correct: boolean | null
  theta: number
  theta_se: number
  items_answered: number
  exam_complete: boolean
  grade: string | null
  percentile: number | null
  message: string
}

export interface ExamResult {
  session_id: string
  exam_title: string
  student_name: string
  theta_final: number
  grade: string
  percentile: number
  items_administered: number
  score_percent: number
  status: string
  collusion_flag: boolean
  collusion_probability: number | null
  started_at: string
  completed_at: string | null
}

export interface AnalyticsOverview {
  total_students: number
  total_items: number
  total_exam_sessions: number
  completed_sessions: number
  flagged_for_collusion: number
  avg_theta_all_students: number
}

export interface ExamStats {
  exam_id: string
  exam_title: string
  subject: string
  total_attempts: number
  completed_attempts: number
  avg_theta: number
  avg_items_administered: number
  flagged_for_collusion: number
  grade_distribution: Record<string, number>
  thetas: number[]
}

export interface AuthState {
  user: User | null
  token: string | null
  isLoggedIn: boolean
  setAuth: (user: User, token: string) => void
  clearAuth: () => void
}