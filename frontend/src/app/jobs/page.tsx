"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { jobsApi } from "@/lib/api";
import { JobDescription } from "@/types";
import { isAuthenticated } from "@/lib/auth";
import { cn, formatDate, getStatusColor } from "@/lib/utils";

export default function JobsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<JobDescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [togglingId, setTogglingId] = useState<number | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) { router.replace("/login"); return; }
    loadJobs();
  }, [router]);

  async function loadJobs() {
    try {
      const res = await jobsApi.list();
      setJobs(res.data);
    } finally {
      setLoading(false);
    }
  }

  async function toggleOpen(e: React.MouseEvent, jobId: number) {
    e.preventDefault();
    e.stopPropagation();
    setTogglingId(jobId);
    try {
      const res = await jobsApi.toggleOpen(jobId);
      setJobs(prev => prev.map(j => j.id === jobId ? { ...j, is_open: res.data.is_open } : j));
    } finally {
      setTogglingId(null);
    }
  }

  const filtered = filter ? jobs.filter(j => j.status === filter) : jobs;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Job Descriptions</h1>
          <p className="text-gray-500 text-sm mt-0.5">{jobs.length} vị trí tuyển dụng</p>
        </div>
        <Link
          href="/jobs/create"
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Tạo JD mới
        </Link>
      </div>

      <div className="flex gap-2 mb-4">
        {["", "draft", "published", "archived"].map(s => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={cn(
              "px-3 py-1.5 rounded-full text-sm font-medium border transition-colors",
              filter === s
                ? "bg-indigo-600 text-white border-indigo-600"
                : "bg-white text-gray-600 border-gray-300 hover:border-gray-400"
            )}
          >
            {s === "" ? "Tất cả" : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Đang tải...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-gray-500">Chưa có Job Description nào</p>
          <Link href="/jobs/create" className="mt-3 inline-block text-indigo-600 text-sm font-medium hover:underline">
            Tạo JD đầu tiên →
          </Link>
        </div>
      ) : (
        <div className="grid gap-3">
          {filtered.map(job => (
            <Link
              key={job.id}
              href={`/jobs/${job.id}`}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:border-indigo-300 hover:shadow-sm transition-all group"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <h2 className="font-semibold text-gray-900 group-hover:text-indigo-700 truncate">{job.title}</h2>
                    <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium shrink-0", getStatusColor(job.status))}>
                      {job.status}
                    </span>
                    <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium shrink-0", job.is_open ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-red-50 text-red-600 border-red-200")}>
                      {job.is_open ? "Open" : "Closed"}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <span>{job.department}</span>
                    <span>•</span>
                    <span>{job.seniority_level}</span>
                    <span>•</span>
                    <span>{job.candidate_count} ứng viên</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-4">
                  <button
                    onClick={(e) => toggleOpen(e, job.id)}
                    disabled={togglingId === job.id}
                    className={cn(
                      "text-xs px-2.5 py-1 rounded-lg font-medium border transition-colors disabled:opacity-50",
                      job.is_open
                        ? "bg-red-50 text-red-600 border-red-200 hover:bg-red-100"
                        : "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
                    )}
                  >
                    {togglingId === job.id ? "..." : job.is_open ? "Đóng vị trí" : "Mở vị trí"}
                  </button>
                  <div className="text-xs text-gray-400">{formatDate(job.created_at)}</div>
                </div>
              </div>
              <div className="flex flex-wrap gap-1.5 mt-3">
                {(job.required_skills ?? []).slice(0, 4).map(skill => (
                  <span key={skill} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-md">{skill}</span>
                ))}
                {(job.required_skills?.length ?? 0) > 4 && (
                  <span className="text-xs text-gray-400">+{job.required_skills.length - 4}</span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
