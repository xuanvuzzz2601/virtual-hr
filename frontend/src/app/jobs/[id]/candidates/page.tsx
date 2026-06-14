"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { candidatesApi, jobsApi } from "@/lib/api";
import { Candidate, JobDescription } from "@/types";
import { cn, formatDate, getRecommendationColor, getRecommendationLabel, getScoreColor } from "@/lib/utils";

export default function CandidatesPage() {
  const { id } = useParams<{ id: string }>();
  const jdId = Number(id);
  const [job, setJob] = useState<JobDescription | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [sortBy, setSortBy] = useState("overall_score");
  const [filterLevel, setFilterLevel] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const [jobRes, candRes] = await Promise.all([
        jobsApi.get(jdId),
        candidatesApi.listByJob(jdId, { sort_by: sortBy, recommendation_level: filterLevel || undefined }),
      ]);
      setJob(jobRes.data);
      setCandidates(candRes.data);
    } finally {
      setLoading(false);
    }
  }, [jdId, sortBy, filterLevel]);

  useEffect(() => { load(); }, [load]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg("Đang upload và phân tích CV...");
    try {
      await candidatesApi.upload(jdId, file);
      setUploadMsg("Upload thành công! AI đang xếp hạng ứng viên...");
      await load();
      setUploadMsg("");
    } catch {
      setUploadMsg("Upload thất bại. Vui lòng thử lại.");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  const sorted = [...candidates].sort((a, b) => {
    if (sortBy === "overall_score") return (b.overall_score ?? 0) - (a.overall_score ?? 0);
    if (sortBy === "created_at") return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    return 0;
  });

  return (
    <div>
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <Link href="/jobs" className="hover:text-gray-800">Job Descriptions</Link>
        <span>/</span>
        <Link href={`/jobs/${id}`} className="hover:text-gray-800 truncate max-w-xs">{job?.title}</Link>
        <span>/</span>
        <span className="text-gray-900 font-medium">Ứng viên</span>
      </div>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Danh sách ứng viên</h1>
          <p className="text-gray-500 text-sm">{candidates.length} ứng viên cho {job?.title}</p>
        </div>
        <div>
          <input ref={fileRef} type="file" accept=".pdf,.docx" onChange={handleUpload} className="hidden" />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            {uploading ? "Đang xử lý..." : "Upload CV"}
          </button>
        </div>
      </div>

      {uploadMsg && (
        <div className={cn("mb-4 px-4 py-3 rounded-lg text-sm border", uploading ? "bg-blue-50 border-blue-200 text-blue-700" : uploadMsg.includes("thất bại") ? "bg-red-50 border-red-200 text-red-700" : "bg-green-50 border-green-200 text-green-700")}>
          {uploadMsg}
        </div>
      )}

      <div className="flex gap-3 mb-4">
        <select value={sortBy} onChange={e => setSortBy(e.target.value)} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500">
          <option value="overall_score">Sắp xếp: Score</option>
          <option value="created_at">Sắp xếp: Ngày upload</option>
        </select>
        <select value={filterLevel} onChange={e => setFilterLevel(e.target.value)} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500">
          <option value="">Tất cả mức độ</option>
          <option value="strong_match">Strong Match</option>
          <option value="moderate_match">Moderate Match</option>
          <option value="weak_match">Weak Match</option>
        </select>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Đang tải...</div>
      ) : sorted.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          <p className="text-gray-500">Chưa có ứng viên nào</p>
          <p className="text-gray-400 text-sm mt-1">Upload CV để bắt đầu phân tích</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sorted.map((c, idx) => (
            <Link
              key={c.id}
              href={`/jobs/${id}/candidates/${c.id}`}
              className="bg-white rounded-xl border border-gray-200 p-5 flex items-center gap-4 hover:border-indigo-300 hover:shadow-sm transition-all group"
            >
              <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center text-sm font-medium text-gray-500 shrink-0">
                {idx + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <h3 className="font-semibold text-gray-900 group-hover:text-indigo-700">{c.name}</h3>
                  {c.recommendation_level && (
                    <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", getRecommendationColor(c.recommendation_level))}>
                      {getRecommendationLabel(c.recommendation_level)}
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-500">{c.email} · {c.cv_filename}</p>
              </div>
              <div className="grid grid-cols-3 gap-3 shrink-0">
                {[
                  { label: "Skills", val: c.skills_match },
                  { label: "Exp", val: c.experience_match },
                  { label: "Overall", val: c.overall_score },
                ].map(({ label, val }) => (
                  <div key={label} className="text-center">
                    <p className={cn("text-lg font-bold", getScoreColor(val))}>
                      {val != null ? val.toFixed(0) : "—"}
                    </p>
                    <p className="text-xs text-gray-400">{label}</p>
                  </div>
                ))}
              </div>
              <div className="text-xs text-gray-400 shrink-0">{formatDate(c.created_at)}</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
