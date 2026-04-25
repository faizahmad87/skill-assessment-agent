export interface CandidateSkill {
  skill: string;
  years_experience?: number;
  evidence?: string;
}

export interface AnalyzeResponse {
  session_id: string;
  required_skills: string[];
  candidate_skills: CandidateSkill[];
  first_message: string;
}

export interface SkillScore {
  skill: string;
  score: number;
  status_label: 'Strong' | 'Adequate' | 'Gap' | 'Critical Gap';
  notes: string;
}

export interface LearningResource {
  title: string;
  url: string;
  type: 'course' | 'video' | 'docs' | 'book';
  is_free: boolean;
}

export interface LearningItem {
  skill: string;
  priority: number;
  gap_size: string;
  estimated_hours: number;
  resources: LearningResource[];
  project_idea: string;
  weekly_plan: string;
}

export interface ReportResponse {
  session_id: string;
  overall_score: number;
  readiness_label: string;
  weeks_to_ready: number;
  skill_scores: SkillScore[];
  learning_plan: LearningItem[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
}
