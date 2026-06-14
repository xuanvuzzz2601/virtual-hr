"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { candidatesApi, interviewsApi, jobsApi } from "@/lib/api";
import { Candidate, InterviewSession, JobDescription } from "@/types";
import { cn, formatDate, getRecommendationColor, getRecommendationLabel, getScoreColor } from "@/lib/utils";

function ScoreBar({ label, score }: { label: string; score?: number | null }) {
  const val = score ?? 0;
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className={cn("font-semibold", getScoreColor(score))}>{score != null ? score.toFixed(1) : "—"}</span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2">
        <div
          className={cn("h-2 rounded-full transition-all", val >= 80 ? "bg-green-500" : val >= 60 ? "bg-yellow-500" : "bg-red-400")}
          style={{ width: `${val}%` }}
        />
      </div>
    </div>
  );
}

function CredentialsModal({
  session,
  candidateName,
  onClose,
  onGo,
}: {
  session: InterviewSession;
  candidateName: string;
  onClose: () => void;
  onGo: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const email = session.candidate_plain_password
    ? `${candidateName.toLowerCase().replace(/\s+/g, "").slice(0, 12)}_${session.id}@interview.virtualhr`
    : "—";

  function copyAll() {
    const text = `Email: ${email}\nMật khẩu: ${session.candidate_plain_password}`;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-gray-900">Tài khoản phỏng vấn đã được tạo</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 mb-5">
          <p className="text-sm text-indigo-700 mb-3 font-medium">
            Gửi thông tin đăng nhập này cho ứng viên <span className="font-bold">{candidateName}</span>:
          </p>
          <div className="space-y-2">
            <div className="bg-white rounded-lg px-3 py-2 flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-400 mb-0.5">Email đăng nhập</p>
                <p className="text-sm font-mono text-gray-800 break-all">{email}</p>
              </div>
            </div>
            <div className="bg-white rounded-lg px-3 py-2 flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-400 mb-0.5">Mật khẩu</p>
                <p className="text-sm font-mono text-gray-800 tracking-widest">{session.candidate_plain_password}</p>
              </div>
            </div>
          </div>
          <button
            onClick={copyAll}
            className="mt-3 w-full text-sm text-indigo-600 border border-indigo-300 rounded-lg py-1.5 hover:bg-indigo-100 transition-colors"
          >
            {copied ? "✓ Đã copy!" : "Copy thông tin đăng nhập"}
          </button>
        </div>

        <p className="text-xs text-gray-500 mb-5 text-center">
          Ứng viên đăng nhập tại <span className="font-medium">trang login</span> và sẽ được chuyển thẳng vào phòng phỏng vấn.
        </p>

        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 py-2.5 border border-gray-300 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50">
            Đóng
          </button>
          <button onClick={onGo} className="flex-1 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700">
            Vào phòng phỏng vấn (HR)
          </button>
        </div>
      </div>
    </div>
  );
}

export default function CandidateDetailPage() {
  const { id, candidateId } = useParams<{ id: string; candidateId: string }>();
  const router = useRouter();
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [job, setJob] = useState<JobDescription | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [createdSession, setCreatedSession] = useState<InterviewSession | null>(null);

  useEffect(() => {
    Promise.all([candidatesApi.get(Number(candidateId)), jobsApi.get(Number(id))])
      .then(([cRes, jRes]) => { setCandidate(cRes.data); setJob(jRes.data); })
      .catch(() => router.replace(`/jobs/${id}/candidates`))
      .finally(() => setLoading(false));
  }, [candidateId, id, router]);

  async function startInterview() {
    setCreating(true);
    try {
      const res = await interviewsApi.create(Number(candidateId), Number(id));
      setCreatedSession(res.data);
    } catch {
      alert("Không thể tạo phỏng vấn. Vui lòng thử lại.");
      setCreating(false);
    }
  }

  function goToInterview() {
    if (!createdSession) return;
    router.push(`/jobs/${id}/candidates/${candidateId}/interview/${createdSession.id}`);
  }

  if (loading) return <div className="text-center py-12 text-gray-400">Đang tải...</div>;
  if (!candidate) return null;

  return (
    <div className="max-w-4xl mx-auto">
      {createdSession && candidate && (
        <CredentialsModal
          session={createdSession}
          candidateName={candidate.name}
          onClose={() => { setCreatedSession(null); setCreating(false); }}
          onGo={goToInterview}
        />
      )}

      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <Link href="/jobs" className="hover:text-gray-800">Jobs</Link>
        <span>/</span>
        <Link href={`/jobs/${id}`} className="hover:text-gray-800 truncate max-w-[120px]">{job?.title}</Link>
        <span>/</span>
        <Link href={`/jobs/${id}/candidates`} className="hover:text-gray-800">Ứng viên</Link>
        <span>/</span>
        <span className="text-gray-900 font-medium">{candidate.name}</span>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Left: Profile */}
        <div className="col-span-2 space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-xl font-bold text-gray-900">{candidate.name}</h1>
                <p className="text-gray-500 text-sm mt-0.5">{candidate.email}{candidate.phone ? ` · ${candidate.phone}` : ""}</p>
                <p className="text-gray-400 text-xs mt-1">CV: {candidate.cv_filename} · Upload {formatDate(candidate.created_at)}</p>
              </div>
              {candidate.recommendation_level && (
                <span className={cn("text-sm px-3 py-1 rounded-full border font-medium", getRecommendationColor(candidate.recommendation_level))}>
                  {getRecommendationLabel(candidate.recommendation_level)}
                </span>
              )}
            </div>
          </div>

          {candidate.skills && candidate.skills.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-800 mb-3">Skills</h3>
              <div className="flex flex-wrap gap-2">
                {candidate.skills.map(s => <span key={s} className="bg-gray-100 text-gray-700 text-sm px-2.5 py-1 rounded-md">{s}</span>)}
              </div>
            </div>
          )}

          {candidate.work_experience && candidate.work_experience.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-800 mb-3">Kinh nghiệm làm việc</h3>
              <div className="space-y-3">
                {candidate.work_experience.map((exp, i) => (
                  <div key={i} className="border-l-2 border-gray-200 pl-3">
                    <p className="font-medium text-gray-800">{exp.title} · {exp.company}</p>
                    <p className="text-xs text-gray-500 mb-1">{exp.duration}</p>
                    {exp.responsibilities?.slice(0, 3).map((r, j) => (
                      <p key={j} className="text-sm text-gray-600">• {r}</p>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}

          {candidate.education && candidate.education.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-800 mb-3">Học vấn</h3>
              <div className="space-y-2">
                {candidate.education.map((edu, i) => (
                  <div key={i}>
                    <p className="font-medium text-gray-800">{edu.degree} in {edu.field}</p>
                    <p className="text-sm text-gray-500">{edu.institution} · {edu.year}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: Scores + Actions */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-800 mb-4">AI Evaluation Score</h3>
            {candidate.overall_score != null ? (
              <>
                <div className="text-center mb-4">
                  <p className={cn("text-4xl font-bold", getScoreColor(candidate.overall_score))}>
                    {candidate.overall_score.toFixed(0)}
                  </p>
                  <p className="text-sm text-gray-500">Overall Score</p>
                </div>
                <div className="space-y-3">
                  <ScoreBar label="Skills Match" score={candidate.skills_match} />
                  <ScoreBar label="Experience" score={candidate.experience_match} />
                  <ScoreBar label="Education" score={candidate.education_match} />
                  <ScoreBar label="Domain Knowledge" score={candidate.domain_knowledge} />
                  <ScoreBar label="Communication" score={candidate.communication_indicators} />
                </div>
                {candidate.ranking_summary && (
                  <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-500 leading-relaxed">{candidate.ranking_summary}</p>
                  </div>
                )}
              </>
            ) : (
              <p className="text-gray-400 text-sm">Đang phân tích...</p>
            )}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-800 mb-3">Phỏng vấn ảo</h3>
            <p className="text-sm text-gray-500 mb-3">
              Tạo phòng phỏng vấn và sinh tài khoản để ứng viên đăng nhập phỏng vấn với AI Interviewer (Gemini Live)
            </p>
            <button
              onClick={startInterview}
              disabled={creating}
              className="w-full bg-indigo-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
              {creating ? "Đang tạo..." : "Tạo phòng phỏng vấn"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
