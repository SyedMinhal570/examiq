// lib/utils.ts
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function gradeColor(grade: string): string {
  if (grade.startsWith("A")) return "text-emerald-400"
  if (grade.startsWith("B")) return "text-blue-400"
  if (grade.startsWith("C")) return "text-yellow-400"
  return "text-red-400"
}

export function gradeBg(grade: string): string {
  if (grade.startsWith("A")) return "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
  if (grade.startsWith("B")) return "bg-blue-500/10 border-blue-500/30 text-blue-400"
  if (grade.startsWith("C")) return "bg-yellow-500/10 border-yellow-500/30 text-yellow-400"
  return "bg-red-500/10 border-red-500/30 text-red-400"
}

export function thetaToPercent(theta: number): number {
  // Map theta (-4 to +4) to 0-100 for progress bars
  return Math.round(((theta + 4) / 8) * 100)
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-PK", {
    day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  })
}

export function formatDuration(startIso: string, endIso?: string): string {
  const start = new Date(startIso).getTime()
  const end = endIso ? new Date(endIso).getTime() : Date.now()
  const diffMin = Math.round((end - start) / 60000)
  if (diffMin < 60) return `${diffMin} min`
  return `${Math.floor(diffMin / 60)}h ${diffMin % 60}m`
}