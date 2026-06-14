import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getRecommendationColor(level?: string | null) {
  switch (level) {
    case "strong_match": return "text-green-600 bg-green-50 border-green-200";
    case "moderate_match": return "text-yellow-600 bg-yellow-50 border-yellow-200";
    case "weak_match": return "text-red-600 bg-red-50 border-red-200";
    default: return "text-gray-500 bg-gray-50 border-gray-200";
  }
}

export function getRecommendationLabel(level?: string | null) {
  switch (level) {
    case "strong_match": return "Strong Match";
    case "moderate_match": return "Moderate Match";
    case "weak_match": return "Weak Match";
    default: return "Pending";
  }
}

export function getStatusColor(status: string) {
  switch (status) {
    case "published": return "text-green-600 bg-green-50 border-green-200";
    case "draft": return "text-yellow-600 bg-yellow-50 border-yellow-200";
    case "archived": return "text-gray-500 bg-gray-50 border-gray-200";
    default: return "text-gray-500 bg-gray-50 border-gray-200";
  }
}

export function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("vi-VN", {
    day: "2-digit", month: "2-digit", year: "numeric",
  });
}

export function getScoreColor(score?: number | null) {
  if (!score) return "text-gray-400";
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  return "text-red-500";
}
