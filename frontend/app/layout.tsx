// app/layout.tsx
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { Toaster } from "react-hot-toast"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "ExamIQ — Adaptive Exam Intelligence",
  description: "AI-powered adaptive testing with anti-cheat detection. Built at ITU Lahore.",
  icons: { icon: "/favicon.ico" },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-gray-950 text-gray-100 antialiased`}>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "#1f2937",
              color: "#f9fafb",
              border: "1px solid #374151",
            },
            success: { iconTheme: { primary: "#10b981", secondary: "#f9fafb" } },
            error:   { iconTheme: { primary: "#ef4444", secondary: "#f9fafb" } },
          }}
        />
      </body>
    </html>
  )
}