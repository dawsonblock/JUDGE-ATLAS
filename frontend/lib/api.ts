export type EventItem = {
  event_id: string;
  court_id: number;
  judge_id: number | null;
  case_id: number;
  primary_location_id: number;
  event_type: string;
  event_subtype: string | null;
  decision_result: string | null;
  decision_date: string | null;
  posted_date: string | null;
  title: string;
  summary: string;
  repeat_offender_indicator: boolean;
  repeat_offender_indicators: string[];
  verification_status: string | null;
  source_excerpt: string | null;
  is_mappable: boolean;
  location_status: "mapped" | "court_location_pending";
  verified_flag: boolean;
  source_quality: string;
  review_status: string;
  court?: { id: number; name: string; courtlistener_id: string; region: string | null } | null;
  judge?: { id: number; name: string } | null;
  defendants: { id: number; anonymized_id: string; display_label: string }[];
  sources: { id: number; source_id: string; source_type: string; title: string; url: string; source_quality: string; verified_flag: boolean; review_status: string }[];
  outcomes: { id: number; outcome_type: string; outcome_date: string | null; summary: string }[];
  outcome_status: string | null;
};

export type MapFeature = {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: {
    record_type: "court_event";
    event_id: string;
    judge_id: number | null;
    judge_name: string;
    court_id: number | null;
    court_name: string | null;
    location_id: number;
    location_name: string;
    title: string;
    event_type: string;
    event_date: string | null;
    case_id: number | null;
    case_name: string | null;
    case_number: string | null;
    decision_date: string | null;
    court: string | null;
    judge: string | null;
    repeat_offender_indicator: boolean;
    verified_flag: boolean;
    review_status: string;
    location_status: "mapped";
    is_mappable: true;
    source_quality: string;
    defendants: string[];
    source_count: number;
    has_news: boolean;
    has_incident_links: boolean;
    disclaimer: string;
  };
};

export type FeatureCollection = {
  type: "FeatureCollection";
  features: MapFeature[];
  returned_count: number;
  truncated: boolean;
  filters_applied: Record<string, unknown>;
  disclaimer: string;
};

export type CrimeIncidentFeature = {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: {
    record_type: "reported_incident";
    incident_id: number;
    incident_type: string;
    incident_category: string;
    reported_at: string | null;
    occurred_at: string | null;
    city: string | null;
    province_state: string | null;
    country: string | null;
    area_label: string | null;
    precision_level: string;
    source_name: string;
    source_url: string | null;
    verification_status: string;
    review_status: string;
    source_count: number;
    has_news: boolean;
    has_court_links: boolean;
    is_aggregate: boolean;
    disclaimer: string;
  };
};

export type SourceLink = {
  label: string;
  url: string;
  source_type: string;
  supports_claim: string;
  retrieved_at: string | null;
};

export type RelatedCourtRecord = {
  event_id: string;
  case_name: string | null;
  judge_name: string | null;
  decision_type: string;
  date: string | null;
  relationship_status: string;
  url: string | null;
};

export type RelatedIncident = {
  incident_id: number;
  category: string;
  date: string | null;
  city: string | null;
  relationship_status: string;
};

export type RecordAudit = {
  review_status: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  last_updated: string | null;
};

export type RecordDetail = {
  record_type: "court_event" | "reported_incident";
  id: string | number;
  title?: string;
  event_type?: string;
  event_subtype?: string | null;
  date: string | null;
  court_name?: string | null;
  court_location?: string | null;
  judge_name?: string | null;
  case_name?: string | null;
  docket_number?: string | null;
  category?: string;
  incident_type?: string;
  city?: string | null;
  state_province?: string | null;
  country?: string | null;
  area_label?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  precision_level?: string;
  summary: string;
  source_links: SourceLink[];
  news_articles: SourceLink[];
  related_court_records: RelatedCourtRecord[];
  related_reported_incidents: RelatedIncident[];
  audit: RecordAudit;
  disclaimer: string;
  news_context_note: string;
};

export type MapDotRecord = {
  id: string | number;
  record_type: "court_event" | "reported_incident";
  latitude: number;
  longitude: number;
  title: string;
  date: string | null;
  city: string | null;
  state_province?: string | null;
  source_count: number;
  has_news: boolean;
  disclaimer: string;
};

export type SourcePanelItem = {
  source_name: string;
  source_type: string;
  source_url: string | null;
  retrieved_at: string | null;
  published_at: string | null;
  quoted_excerpt: string | null;
  verification_status: string;
  trust_reason: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_status: string;
};

export type SourcePanelData = {
  entity_type: string;
  entity_id: string | number;
  review_status: string;
  sources: SourcePanelItem[];
};

export type CrimeIncidentFeatureCollection = {
  type: "FeatureCollection";
  features: CrimeIncidentFeature[];
  returned_count: number;
  truncated: boolean;
  filters_applied: Record<string, unknown>;
  disclaimer: string;
};

const publicBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const serverBase = process.env.BACKEND_INTERNAL_URL || publicBase;

export function apiBase(isServer = typeof window === "undefined") {
  return isServer ? serverBase : publicBase;
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase()}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
