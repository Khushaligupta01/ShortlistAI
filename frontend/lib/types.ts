export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  display_name: string | null;
  role: "recruiter" | "client_hiring_manager" | "delivery_head";
  organization_id: string | null;
  is_active: boolean;
}

export interface ApiError {
  error_code: string;
  message: string;
  trace_id: string;
}

export interface Requisition {
  id: string;
  organization_id: string;
  created_by: string;
  title: string;
  job_description: string;
  status: "draft" | "active" | "archived";
  created_at: string;
  updated_at: string;
  version: number;
}

export interface RequisitionListResponse {
  items: Requisition[];
  total: number;
  page: number;
  page_size: number;
}

export interface Organization {
  id: string;
  name: string;
  org_type: "staffing_firm" | "client_company";
  created_at: string;
}

export interface MembershipInfo {
  organization: Organization;
  role: string;
  is_active: boolean;
}
