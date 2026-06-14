"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { jobsApi } from "@/lib/api";
import { JobDescription } from "@/types";
import { cn, formatDate, getStatusColor } from "@/lib/utils";

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [job, setJob] = useState<JobDescription | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => { loadJob(); }, [id]);

  async function loadJob() {
    try {
      const res = await jobsApi.get(Number(id));
      setJob(res.data);
    } catch {
      router.replace("/jobs");
    } finally {
      setLoading(false);
    }
  }

  async function handlePublish() {
    setActionLoading(true);
    try {
      await jobsApi.publish(Number(id));
      await loadJob();
    } finally { setActionLoading(false); }
  }

  async function handleArchive() {
    if (!confirm("Bạn có chắc muốn archive JD này?")) return;
    setActionLoading(true);
    try {
      await jobsApi.archive(Number(id));
      await loadJob();
    } finally { setActionLoading(false); }
  }

  async function handleToggleOpen() {
    setActionLoading(true);
    try {
      await jobsApi.toggleOpen(Number(id));
      await loadJob();
    } finally { setActionLoading(false); }
  }

  async function handleDelete() {
    if (!confirm("Xóa JD này? Hành động này không thể hoàn tác.")) return;
    setActionLoading(true);
    try {
      await jobsApi.delete(Number(id));
      router.push("/jobs");
    } finally { setActionLoading(false); }
  }

  if (loading) return <div className="text-center py-12 text-gray-400">Đang tải...</div>;
  if (!job) return null;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <Link href="/jobs" className="hover:text-gray-800">Job Descriptions</Link>
        <span>/</span>
        <span className="text-gray-900 font-medium truncate">{job.title}</span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-4">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold text-gray-900">{job.title}</h1>
              <span className={cn("text-xs px-2.5 py-1 rounded-full border font-medium", getStatusColor(job.status))}>
                {job.status}
              </span>
              <span className={cn("text-xs px-2.5 py-1 rounded-full border font-medium", job.is_open ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-red-50 text-red-600 border-red-200")}>
                {job.is_open ? "Open" : "Closed"}
              </span>
            </div>
            <p className="text-gray-500">{job.department} · {job.seniority_level} · {job.experience_requirements}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0 ml-4">
            {job.status === "draft" && (
              <button onClick={handlePublish} disabled={actionLoading} className="px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50">
                Publish
              </button>
            )}
            {job.status === "published" && (
              <button onClick={handleArchive} disabled={actionLoading} className="px-3 py-1.5 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300 disabled:opacity-50">
                Archive
              </button>
            )}
            <button
              onClick={handleToggleOpen}
              disabled={actionLoading}
              className={cn(
                "px-3 py-1.5 text-sm rounded-lg border font-medium disabled:opacity-50",
                job.is_open
                  ? "bg-red-50 text-red-600 border-red-200 hover:bg-red-100"
                  : "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
              )}
            >
              {job.is_open ? "Đóng vị trí" : "Mở vị trí"}
            </button>
            <Link href={`/jobs/${id}/edit`} className="px-3 py-1.5 border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50">
              Edit
            </Link>
            <button onClick={handleDelete} disabled={actionLoading} className="px-3 py-1.5 border border-red-200 text-red-600 text-sm rounded-lg hover:bg-red-50 disabled:opacity-50">
              Xóa
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-6 text-sm">
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-gray-500 text-xs mb-0.5">Ngày tạo</p>
            <p className="font-medium text-gray-800">{formatDate(job.created_at)}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-gray-500 text-xs mb-0.5">Ứng viên</p>
            <p className="font-medium text-gray-800">{job.candidate_count} người</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <h3 className="font-semibold text-gray-800 mb-2">Trách nhiệm</h3>
            <p className="text-gray-600 text-sm whitespace-pre-wrap leading-relaxed">{job.responsibilities}</p>
          </div>
          <div>
            <h3 className="font-semibold text-gray-800 mb-2">Required Skills</h3>
            <div className="flex flex-wrap gap-2">
              {job.required_skills.map(s => <span key={s} className="bg-indigo-50 text-indigo-700 text-sm px-2.5 py-1 rounded-full border border-indigo-200">{s}</span>)}
            </div>
          </div>
          {job.preferred_skills?.length > 0 && (
            <div>
              <h3 className="font-semibold text-gray-800 mb-2">Preferred Skills</h3>
              <div className="flex flex-wrap gap-2">
                {job.preferred_skills.map(s => <span key={s} className="bg-gray-100 text-gray-600 text-sm px-2.5 py-1 rounded-full border border-gray-200">{s}</span>)}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Ứng viên ({job.candidate_count})</h2>
        <Link
          href={`/jobs/${id}/candidates`}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          Xem tất cả ứng viên →
        </Link>
      </div>
    </div>
  );
}
