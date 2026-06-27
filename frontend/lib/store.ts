// lib/store.ts — Global state with Zustand
import { create } from "zustand"
import { persist, createJSONStorage } from "zustand/middleware"
import type { User } from "@/types"

interface AuthState {
  user: User | null
  token: string | null
  setAuth: (user: User, token: string) => void
  clearAuth: () => void
  isLoggedIn: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      setAuth: (user, token) => set({ user, token }),
      clearAuth: () => set({ user: null, token: null }),
      isLoggedIn: () => !!get().token,
    }),
    {
      name: "examiq-auth",
      storage: createJSONStorage(() => sessionStorage),
    }
  )
)