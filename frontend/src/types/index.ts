export interface User {
  id: number;
  email: string;
  name: string;
  role: "admin" | "hr" | "hiring_manager" | "candidate";
  is_active: boolean;
  created_at: string;
}

export interface JobDescription {
  id: number;
  title: string;
  department: string;
  seniority_level: string;
  responsibilities: string;
  required_skills: string[];
  preferred_skills: string[];
  experience_requirements: string;
  status: "draft" | "published" | "archived";
  is_open: boolean;
  created_by: number;
  created_at: string;
  updated_at: string;
  candidate_count: number;
  creator?: User;
}

export interface Candidate {
  id: number;
  jd_id: number;
  name: string;
  email: string;
  phone?: string;
  skills: string[];
  education: Education[];
  work_experience: WorkExperience[];
  certifications: string[];
  cv_filename: string;
  cv_file_path: string;
  overall_score?: number;
  skills_match?: number;
  experience_match?: number;
  education_match?: number;
  domain_knowledge?: number;
  communication_indicators?: number;
  recommendation_level?: "strong_match" | "moderate_match" | "weak_match";
  ranking_summary?: string;
  created_at: string;
}

export interface Education {
  institution: string;
  degree: string;
  field: string;
  year: string;
}

export interface WorkExperience {
  company: string;
  title: string;
  duration: string;
  responsibilities: string[];
}

export interface InterviewSession {
  id: number;
  candidate_id: number;
  jd_id: number;
  status: "pending" | "in_progress" | "completed" | "cancelled";
  transcript?: TranscriptMessage[];
  started_at?: string;
  completed_at?: string;
  created_at: string;
  candidate_user_id?: number;
  candidate_plain_password?: string;
}

export interface TranscriptMessage {
  role: "interviewer" | "candidate";
  content: string;
  timestamp?: string;
}

export interface InterviewEvaluation {
  id: number;
  session_id: number;
  technical_knowledge: number;
  communication_skills: number;
  problem_solving: number;
  confidence: number;
  role_fit: number;
  overall_score: number;
  strengths: string[];
  weaknesses: string[];
  summary: string;
  recommendation: string;
  created_at: string;
}

export interface GeminiSessionConfig {
  system_prompt: string;
  candidate_name: string;
  job_title: string;
  session_id: number;
  gemini_api_key?: string;
}
