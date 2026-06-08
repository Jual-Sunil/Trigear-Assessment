// ─── Auth ────────────────────────────────────────────────────────────────────

export interface LoginResponse {
  authorization_url: string;
}

export interface CallbackResponse {
  success: boolean;
}

// ─── Dashboard ───────────────────────────────────────────────────────────────

export interface DashboardResponse {
  total_emails: number;
  important_emails: number;
  pending_tasks: number;
  upcoming_interviews: number;
  active_jobs: number;
}

// ─── Email ───────────────────────────────────────────────────────────────────

export interface EmailSummary {
  id: string;
  subject: string | null;
  sender_name: string | null;
  sender_email: string;
  received_at: string;
  classification: string | null;
  confidence_score: number | null;
  priority_score: number | null;
  summary: string | null;
  is_action_required: boolean | null;
  snippet: string | null;
}

export interface EmailDetail extends EmailSummary {
  body_text: string | null;
  body_html: string | null;
  gmail_message_id: string;
  gmail_thread_id: string;
}

export interface EmailListResponse {
  items: EmailSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface EmailListParams {
  classification?: string;
  priority_min?: number;
  page?: number;
  page_size?: number;
}

// ─── Task ────────────────────────────────────────────────────────────────────

export interface Task {
  id: string;
  email_id: string;
  title: string | null;
  description: string | null;
  priority: number | null;
  status: string | null;
  due_date: string | null;
}

export interface TaskListResponse {
  items: Task[];
}

export interface TaskUpdateRequest {
  status?: string;
  priority?: number;
  due_date?: string;
}

export interface TaskUpdateResponse {
  success: boolean;
}

// ─── Job Opportunity ─────────────────────────────────────────────────────────

export interface JobOpportunity {
  id: string;
  email_id: string;
  company: string | null;
  role: string | null;
  location: string | null;
  salary: string | null;
  apply_link: string | null;
  deadline: string | null;
}

export interface JobListResponse {
  items: JobOpportunity[];
}

// ─── Interview ───────────────────────────────────────────────────────────────

export interface Interview {
  id: string;
  email_id: string;
  company: string | null;
  role: string | null;
  interview_date: string | null;
  meeting_link: string | null;
}

export interface InterviewListResponse {
  items: Interview[];
}

// ─── Search ──────────────────────────────────────────────────────────────────

export interface SearchResult {
  email_id: string;
  subject: string | null;
  sender_email: string;
  received_at: string;
  summary: string | null;
  score: number;
}

export interface SearchResponse {
  items: SearchResult[];
  query: string;
}

export interface SearchParams {
  q: string;
  limit?: number;
}

// ─── Sync ────────────────────────────────────────────────────────────────────

export interface SyncResponse {
  synced: number;
  skipped: number;
}

// ─── Pagination ──────────────────────────────────────────────────────────────

export interface PaginationMeta {
  total: number;
  page: number;
  page_size: number;
}