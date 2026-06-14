"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { interviewsApi } from "@/lib/api";
import { getUser, isAuthenticated, clearAuth } from "@/lib/auth";
import { InterviewSession } from "@/types";
import { cn } from "@/lib/utils";

export default function CandidateInterviewPage() {
  const router = useRouter();
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const user = getUser();

  useEffect(() => {
    if (!isAuthenticated()) { router.replace("/login"); return; }
    if (user?.role !== "candidate") { router.replace("/jobs"); return; }

    interviewsApi.mySession()
      .then(res => setSession(res.data))
      .catch(() => setError("Không tìm thấy phòng phỏng vấn. Vui lòng liên hệ HR."))
      .finally(() => setLoading(false));
  }, []);

  function handleLogout() {
    clearAuth();
    router.push("/login");
  }

  function startInterview() {
    if (!session) return;
    router.push(`/jobs/${session.jd_id}/candidates/${session.candidate_id}/interview/${session.id}`);
  }

  const statusLabel: Record<string, string> = {
    pending: "Chờ bắt đầu",
    in_progress: "Đang diễn ra",
    completed: "Đã hoàn thành",
    cancelled: "Đã hủy",
  };

  const statusColor: Record<string, string> = {
    pending: "bg-yellow-50 text-yellow-700 border-yellow-200",
    in_progress: "bg-blue-50 text-blue-700 border-blue-200",
    completed: "bg-green-50 text-green-700 border-green-200",
    cancelled: "bg-gray-50 text-gray-500 border-gray-200",
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-blue-100 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <span className="font-semibold text-gray-900">Virtual HR Platform</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">{user?.name}</span>
          <button onClick={handleLogout} className="text-sm text-gray-500 hover:text-gray-800 px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50">
            Đăng xuất
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="bg-white rounded-2xl shadow-lg w-full max-w-md p-8">
          {loading ? (
            <div className="text-center py-8">
              <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-gray-500">Đang tải thông tin phỏng vấn...</p>
            </div>
          ) : error ? (
            <div className="text-center py-6">
              <div className="w-14 h-14 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-7 h-7 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-red-600 font-medium mb-1">Không tìm thấy phòng phỏng vấn</p>
              <p className="text-gray-500 text-sm">{error}</p>
            </div>
          ) : session ? (
            <>
              <div className="text-center mb-6">
                <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                </div>
                <h1 className="text-xl font-bold text-gray-900 mb-1">Phòng phỏng vấn của bạn</h1>
                <p className="text-gray-500 text-sm">Session #{session.id}</p>
              </div>

              <div className="bg-gray-50 rounded-xl p-4 mb-6 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Trạng thái</span>
                  <span className={cn("px-2 py-0.5 rounded-full border text-xs font-medium", statusColor[session.status])}>
                    {statusLabel[session.status]}
                  </span>
                </div>
                {session.started_at && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Bắt đầu lúc</span>
                    <span className="text-gray-700">{new Date(session.started_at).toLocaleString("vi-VN")}</span>
                  </div>
                )}
              </div>

              {session.status === "completed" ? (
                <div className="text-center p-4 bg-green-50 border border-green-200 rounded-xl">
                  <p className="text-green-700 font-medium">Buổi phỏng vấn đã hoàn thành!</p>
                  <p className="text-green-600 text-sm mt-1">Cảm ơn bạn đã tham gia. HR sẽ liên hệ với bạn sớm.</p>
                </div>
              ) : session.status === "cancelled" ? (
                <div className="text-center p-4 bg-gray-50 border border-gray-200 rounded-xl">
                  <p className="text-gray-600 font-medium">Buổi phỏng vấn đã bị hủy</p>
                  <p className="text-gray-500 text-sm mt-1">Vui lòng liên hệ HR để biết thêm thông tin.</p>
                </div>
              ) : (
                <button
                  onClick={startInterview}
                  className="w-full bg-indigo-600 text-white py-3 rounded-xl font-medium hover:bg-indigo-700 flex items-center justify-center gap-2 text-base"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  </svg>
                  {session.status === "in_progress" ? "Tiếp tục phỏng vấn" : "Vào phòng phỏng vấn"}
                </button>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
