"use client";
import Link from "next/link";
import JobForm from "@/components/jobs/JobForm";

export default function CreateJobPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <Link href="/jobs" className="hover:text-gray-800">Job Descriptions</Link>
        <span>/</span>
        <span className="text-gray-900 font-medium">Tạo mới</span>
      </div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Tạo Job Description</h1>
      <JobForm />
    </div>
  );
}
