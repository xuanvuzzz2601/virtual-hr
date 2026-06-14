"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { jobsApi } from "@/lib/api";
import { JobDescription } from "@/types";

interface Props {
  initial?: Partial<JobDescription>;
  jobId?: number;
}

const SENIORITY_LEVELS = ["Intern", "Junior", "Mid-level", "Senior", "Lead", "Manager", "Director"];
const DEPARTMENTS = ["Engineering", "Product", "Design", "Marketing", "Sales", "HR", "Finance", "Operations", "Data", "Security"];

export default function JobForm({ initial, jobId }: Props) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [title, setTitle] = useState(initial?.title ?? "");
  const [department, setDepartment] = useState(initial?.department ?? "");
  const [seniority, setSeniority] = useState(initial?.seniority_level ?? "");
  const [responsibilities, setResponsibilities] = useState(initial?.responsibilities ?? "");
  const [requiredSkills, setRequiredSkills] = useState<string[]>(initial?.required_skills ?? []);
  const [preferredSkills, setPreferredSkills] = useState<string[]>(initial?.preferred_skills ?? []);
  const [experience, setExperience] = useState(initial?.experience_requirements ?? "");
  const [reqInput, setReqInput] = useState("");
  const [prefInput, setPrefInput] = useState("");

  function addSkill(list: string[], setList: (v: string[]) => void, input: string, setInput: (v: string) => void) {
    const val = input.trim();
    if (val && !list.includes(val)) setList([...list, val]);
    setInput("");
  }

  function removeSkill(list: string[], setList: (v: string[]) => void, skill: string) {
    setList(list.filter(s => s !== skill));
  }

  async function handleSave(publish = false) {
    setError("");
    if (!title || !department || !seniority || !responsibilities || requiredSkills.length === 0 || !experience) {
      setError("Vui lòng điền đầy đủ các trường bắt buộc");
      return;
    }
    setLoading(true);
    try {
      const data = { title, department, seniority_level: seniority, responsibilities, required_skills: requiredSkills, preferred_skills: preferredSkills, experience_requirements: experience };
      if (jobId) {
        await jobsApi.update(jobId, data);
        if (publish) await jobsApi.publish(jobId);
        router.push(`/jobs/${jobId}`);
      } else {
        const res = await jobsApi.create(data);
        const id = res.data.id;
        if (publish) await jobsApi.publish(id);
        router.push(`/jobs/${id}`);
      }
    } catch {
      setError("Lưu thất bại. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-6">
      {error && <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Job Title <span className="text-red-500">*</span></label>
          <input value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Senior Backend Engineer" className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Department <span className="text-red-500">*</span></label>
          <select value={department} onChange={e => setDepartment(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm bg-white">
            <option value="">Chọn department</option>
            {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Seniority Level <span className="text-red-500">*</span></label>
          <select value={seniority} onChange={e => setSeniority(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm bg-white">
            <option value="">Chọn level</option>
            {SENIORITY_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Experience Requirements <span className="text-red-500">*</span></label>
          <input value={experience} onChange={e => setExperience(e.target.value)} placeholder="e.g. 3+ years, 2-5 years" className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm" />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Responsibilities <span className="text-red-500">*</span></label>
        <textarea value={responsibilities} onChange={e => setResponsibilities(e.target.value)} rows={5} placeholder="Mô tả các trách nhiệm chính của vị trí..." className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm resize-none" />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Required Skills <span className="text-red-500">*</span></label>
        <div className="flex gap-2 mb-2">
          <input value={reqInput} onChange={e => setReqInput(e.target.value)} onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addSkill(requiredSkills, setRequiredSkills, reqInput, setReqInput))} placeholder="Nhập skill rồi Enter" className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm" />
          <button type="button" onClick={() => addSkill(requiredSkills, setRequiredSkills, reqInput, setReqInput)} className="px-3 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">Thêm</button>
        </div>
        <div className="flex flex-wrap gap-2">
          {requiredSkills.map(s => (
            <span key={s} className="inline-flex items-center gap-1 bg-indigo-50 text-indigo-700 text-sm px-2.5 py-1 rounded-full border border-indigo-200">
              {s}
              <button type="button" onClick={() => removeSkill(requiredSkills, setRequiredSkills, s)} className="text-indigo-400 hover:text-indigo-700">×</button>
            </span>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Preferred Skills</label>
        <div className="flex gap-2 mb-2">
          <input value={prefInput} onChange={e => setPrefInput(e.target.value)} onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addSkill(preferredSkills, setPreferredSkills, prefInput, setPrefInput))} placeholder="Nhập skill rồi Enter" className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm" />
          <button type="button" onClick={() => addSkill(preferredSkills, setPreferredSkills, prefInput, setPrefInput)} className="px-3 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm hover:bg-gray-300">Thêm</button>
        </div>
        <div className="flex flex-wrap gap-2">
          {preferredSkills.map(s => (
            <span key={s} className="inline-flex items-center gap-1 bg-gray-100 text-gray-600 text-sm px-2.5 py-1 rounded-full border border-gray-200">
              {s}
              <button type="button" onClick={() => removeSkill(preferredSkills, setPreferredSkills, s)} className="text-gray-400 hover:text-gray-700">×</button>
            </span>
          ))}
        </div>
      </div>

      <div className="flex gap-3 pt-2">
        <button onClick={() => handleSave(false)} disabled={loading} className="flex-1 bg-white border border-gray-300 text-gray-700 py-2.5 rounded-lg font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors">
          {loading ? "Đang lưu..." : "Lưu Draft"}
        </button>
        <button onClick={() => handleSave(true)} disabled={loading} className="flex-1 bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors">
          {loading ? "Đang lưu..." : "Lưu & Publish"}
        </button>
      </div>
    </div>
  );
}
