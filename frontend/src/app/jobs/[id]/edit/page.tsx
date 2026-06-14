"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { jobsApi } from "@/lib/api";
import { JobDescription } from "@/types";
import JobForm from "@/components/jobs/JobForm";

export default function EditJobPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [job, setJob] = useState<JobDescription | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    jobsApi.get(Number(id))
      .then(res => setJob(res.data))
      .catch(() => router.replace("/jobs"))
      .finally(() => setLoading(false));
  }, [id, router]);

  if (loading) return <div className="text-center py-12 text-gray-400">Đang tải...</div>;
  if (!job) return null;

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <Link href="/jobs" className="hover:text-gray-800">Job Descriptions</Link>
        <span>/</span>
        <Link href={`/jobs/${id}`} className="hover:text-gray-800 truncate max-w-xs">{job.title}</Link>
        <span>/</span>
        <span className="text-gray-900 font-medium">Edit</span>
      </div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Chỉnh sửa JD</h1>
      <JobForm initial={job} jobId={Number(id)} />
    </div>
  );
}
