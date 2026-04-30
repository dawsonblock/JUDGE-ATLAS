"use client";

import { useCallback, useEffect, useState } from "react";
import { apiBase } from "@/lib/api";

type Finding = {
  finding_type: string;
  field_name: string | null;
  expected: string | null;
  found: string | null;
  severity: string;
  note: string | null;
};

type CorrectnessCheck = {
  id: number;
  record_type: string;
  record_id: number;
  model_name: string;
  prompt_version: string;
  event_type_supported: boolean;
  date_supported: boolean;
  location_supported: boolean;
  status_supported: boolean;
  source_supports_claim: boolean;
  duplicate_candidate: boolean;
  possible_duplicate_ids: number[];
  privacy_risk: "low" | "medium" | "high";
  map_quality: string;
  reason: string;
  safe_to_show: boolean;
  checked_at: string;
  findings: Finding[];
};

type FilterKey =
  | "all"
  | "needs_review"
  | "duplicate_candidate"
  | "location_uncertain"
  | "rejected"
  | "privacy_high";

const FILTER_LABELS: Record<FilterKey, string> = {
  all: "All checks",
  needs_review: "Needs review",
  duplicate_candidate: "Duplicate candidates",
  location_uncertain: "Location uncertain",
  rejected: "Rejected",
  privacy_high: "Privacy warnings",
};

const QUALITY_CLASS: Record<string, string> = {
  verified: "aichecks-quality-verified",
  needs_review: "aichecks-quality-needs-review",
  duplicate_candidate: "aichecks-quality-dup",
  location_uncertain: "aichecks-quality-uncertain",
  rejected: "aichecks-quality-rejected",
};

const PRIVACY_CLASS: Record<string, string> = {
  low: "aichecks-privacy-low",
  medium: "aichecks-privacy-medium",
  high: "aichecks-privacy-high",
};

function QualityBadge({ quality }: { quality: string }) {
  const cls = QUALITY_CLASS[quality] ?? "aichecks-quality-default";
  return (
    <span className={`aichecks-quality-badge ${cls}`}>
      {quality.replace(/_/g, " ")}
    </span>
  );
}

function BoolIcon({ value }: { value: boolean }) {
  return value ? (
    <span className="aichecks-bool-yes">✓</span>
  ) : (
    <span className="aichecks-bool-no">✗</span>
  );
}

function CheckRow({
  chk,
  expanded,
  onToggle,
}: {
  chk: CorrectnessCheck;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr className="aichecks-row" onClick={onToggle}>
        <td className="aichecks-td aichecks-td-muted">{chk.id}</td>
        <td className="aichecks-td">{chk.record_type}</td>
        <td className="aichecks-td aichecks-td-mono">{chk.record_id}</td>
        <td className="aichecks-td">
          <QualityBadge quality={chk.map_quality} />
        </td>
        <td className={`aichecks-td ${PRIVACY_CLASS[chk.privacy_risk] ?? ""}`}>
          {chk.privacy_risk}
        </td>
        <td className="aichecks-td aichecks-td-center">
          <BoolIcon value={chk.source_supports_claim} />
        </td>
        <td className="aichecks-td aichecks-td-center">
          <BoolIcon value={chk.date_supported} />
        </td>
        <td className="aichecks-td aichecks-td-center">
          <BoolIcon value={chk.location_supported} />
        </td>
        <td className="aichecks-td aichecks-td-center">
          <BoolIcon value={chk.status_supported} />
        </td>
        <td className="aichecks-td aichecks-td-center">
          {chk.duplicate_candidate ? (
            <span className="aichecks-dup-flag">DUP</span>
          ) : (
            <span className="aichecks-td-muted">—</span>
          )}
        </td>
        <td className="aichecks-td aichecks-td-center">
          <BoolIcon value={chk.safe_to_show} />
        </td>
        <td className="aichecks-td aichecks-td-muted">
          {new Date(chk.checked_at).toLocaleString()}
        </td>
      </tr>
      {expanded && (
        <tr className="aichecks-expanded-row">
          <td colSpan={12} className="aichecks-expanded-cell">
            <p className="aichecks-reason">
              <strong>Reason:</strong> {chk.reason}
            </p>
            {chk.duplicate_candidate && chk.possible_duplicate_ids.length > 0 && (
              <p className="aichecks-dup-ids">
                <strong>Possible duplicate IDs:</strong>{" "}
                {chk.possible_duplicate_ids.join(", ")}
              </p>
            )}
            {chk.findings.length > 0 && (
              <div>
                <p className="aichecks-findings-title">Findings</p>
                <ul className="aichecks-findings-list">
                  {chk.findings.map((f, i) => (
                    <li
                      key={i}
                      className={`aichecks-finding ${
                        f.severity === "error"
                          ? "aichecks-finding-error"
                          : f.severity === "warning"
                          ? "aichecks-finding-warning"
                          : "aichecks-finding-info"
                      }`}
                    >
                      <strong>[{f.severity}] {f.finding_type}</strong>
                      {f.field_name && (
                        <span className="aichecks-field-name"> ({f.field_name})</span>
                      )}
                      {f.note && <span> {f.note}</span>}
                      {f.expected && f.found && (
                        <span className="aichecks-td-muted"> expected: {f.expected} / found: {f.found}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="aichecks-td-muted aichecks-model-line">
              model: {chk.model_name} · prompt: v{chk.prompt_version}
            </p>
          </td>
        </tr>
      )}
    </>
  );
}

export default function AIChecksPage() {
  const [checks, setChecks] = useState<CorrectnessCheck[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterKey>("all");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [token, setToken] = useState("");

  const load = useCallback(async function load() {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: "200" });
      if (filter === "privacy_high") {
        params.set("privacy_risk", "high");
      } else if (filter !== "all") {
        params.set("map_quality", filter);
      }
      const resp = await fetch(
        `${apiBase(false)}/api/admin/correctness/checks?${params}`,
        { headers: { "x-jta-admin-token": token } }
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setChecks(data.checks ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [filter, token]);

  useEffect(() => {
    if (token) load();
  }, [load, token]);

  const counts = {
    all: checks.length,
    needs_review: checks.filter((c) => c.map_quality === "needs_review").length,
    duplicate_candidate: checks.filter((c) => c.duplicate_candidate).length,
    location_uncertain: checks.filter(
      (c) => c.map_quality === "location_uncertain"
    ).length,
    rejected: checks.filter((c) => c.map_quality === "rejected").length,
    privacy_high: checks.filter((c) => c.privacy_risk === "high").length,
  };

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <div className="kicker">Prototype admin</div>
          <h1>AI Correctness Checks</h1>
          <p className="meta">
            Checks map accuracy only — source, location, date, status, duplicates.
            No guilt scores. No judge scores. No danger scores.
          </p>
        </div>
      </div>

      <section className="panel mt-md">
        <h2>Access</h2>
        <div className="admin-review-controls">
          <label className="field">
            <span>Admin token</span>
            <input
              type="password"
              placeholder="Token from JTA_ADMIN_REVIEW_TOKEN"
              value={token}
              onChange={(e) => setToken(e.target.value)}
            />
          </label>
          <button
            className="primary-button"
            type="button"
            onClick={load}
            disabled={!token || loading}
          >
            {loading ? "Loading…" : "Load"}
          </button>
        </div>
        {error && <p className="admin-review-message">{error}</p>}
      </section>

      <section className="panel mt-md">
        <h2>Filter</h2>
        <div className="aichecks-filter-row">
          {(Object.keys(FILTER_LABELS) as FilterKey[]).map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => setFilter(key)}
              className={filter === key ? "aichecks-filter-btn active" : "aichecks-filter-btn"}
            >
              {FILTER_LABELS[key]}
              {counts[key] > 0 && (
                <span className="aichecks-filter-count">{counts[key]}</span>
              )}
            </button>
          ))}
        </div>
      </section>

      {checks.length === 0 && !loading && !error && (
        <p className="meta mt-md">No checks found for this filter.</p>
      )}

      {checks.length > 0 && (
        <section className="panel mt-md">
          <div className="aichecks-table-wrap">
            <table className="source-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Type</th>
                  <th>Record</th>
                  <th>Quality</th>
                  <th>Privacy</th>
                  <th>Source</th>
                  <th>Date</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>Dup</th>
                  <th>Safe</th>
                  <th>Checked</th>
                </tr>
              </thead>
              <tbody>
                {checks.map((chk) => (
                  <CheckRow
                    key={chk.id}
                    chk={chk}
                    expanded={expandedId === chk.id}
                    onToggle={() =>
                      setExpandedId(expandedId === chk.id ? null : chk.id)
                    }
                  />
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </main>
  );
}
