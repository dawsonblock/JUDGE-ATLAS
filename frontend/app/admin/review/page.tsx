"use client";

import Link from "next/link";
import { useState } from "react";
import { apiBase } from "@/lib/api";

type ReviewItem = {
  entity_type: string;
  entity_id: string | number;
  database_id: number;
  title: string | null;
  source_type: string | null;
  review_status: string;
  public_visibility: boolean;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  correction_note: string | null;
  dispute_note: string | null;
};

type ReviewQueueResponse = {
  items: ReviewItem[];
  total_count: number;
};

type AuditEntry = {
  id: number;
  entity_type: string;
  entity_id: number;
  previous_status: string | null;
  new_status: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  notes: string | null;
  public_visibility: boolean;
};

type ReviewHistoryResponse = {
  items: AuditEntry[];
  total_count: number;
};

type AIReviewItem = {
  id: number;
  record_type: string;
  source_quality: string;
  confidence: number;
  privacy_status: string;
  publish_recommendation: string;
  status: string;
  source_url: string | null;
  source_quote: string | null;
  neutral_summary: string | null;
  suggested_payload_json: Record<string, unknown>;
};

type AIReviewQueueResponse = {
  items: AIReviewItem[];
  total_count: number;
};

function formatStatus(status: string | null | undefined) {
  return status ? status.replaceAll("_", " ") : "status pending";
}

export default function AdminReviewPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [aiItems, setAiItems] = useState<AIReviewItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [aiTotalCount, setAiTotalCount] = useState(0);
  const [message, setMessage] = useState("Admin review is disabled by default until JTA_ENABLE_ADMIN_REVIEW and JTA_ADMIN_REVIEW_TOKEN are configured.");
  const [aiMessage, setAiMessage] = useState("AI review items are disabled by default until JTA_ENABLE_ADMIN_IMPORTS=true.");
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [history, setHistory] = useState<AuditEntry[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyMessage, setHistoryMessage] = useState("");
  const [historyLoading, setHistoryLoading] = useState(false);

  async function loadQueue() {
    setLoading(true);
    setMessage("");
    try {
      const response = await fetch(`${apiBase(false)}/api/admin/review-queue?limit=100`, {
        headers: {
          Accept: "application/json",
          "X-JTA-Admin-Token": token,
        },
      });
      if (!response.ok) {
        throw new Error(response.status === 403 ? "Review queue unavailable: admin review is disabled or the token is invalid." : `Review queue failed: ${response.status}`);
      }
      const json = (await response.json()) as ReviewQueueResponse;
      setItems(json.items);
      setTotalCount(json.total_count);
      setMessage(`${json.total_count} evidence record${json.total_count === 1 ? "" : "s"} in review scope.`);
    } catch (error) {
      setItems([]);
      setTotalCount(0);
      setMessage(error instanceof Error ? error.message : "Review queue unavailable.");
    } finally {
      setLoading(false);
    }
  }

  async function actOnQueueItem(entityType: string, entityId: string | number, decision: string) {
    setMessage("");
    try {
      const response = await fetch(
        `${apiBase(false)}/api/admin/review-queue/${entityType}/${entityId}/decision`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
            "X-JTA-Admin-Token": token,
          },
          body: JSON.stringify({ decision, reviewed_by: "admin" }),
        },
      );
      if (!response.ok) {
        throw new Error(`Decision failed: ${response.status}`);
      }
      await loadQueue();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Decision failed.");
    }
  }

  async function loadHistory() {
    setHistoryLoading(true);
    setHistoryMessage("");
    try {
      const response = await fetch(`${apiBase(false)}/api/admin/review-history?limit=50`, {
        headers: { Accept: "application/json", "X-JTA-Admin-Token": token },
      });
      if (!response.ok) {
        throw new Error(response.status === 403 ? "History unavailable: admin review is disabled or token invalid." : `History failed: ${response.status}`);
      }
      const json = (await response.json()) as ReviewHistoryResponse;
      setHistory(json.items);
      setHistoryTotal(json.total_count);
      setHistoryMessage(`${json.total_count} audit record${json.total_count === 1 ? "" : "s"}.`);
    } catch (error) {
      setHistory([]);
      setHistoryTotal(0);
      setHistoryMessage(error instanceof Error ? error.message : "History unavailable.");
    } finally {
      setHistoryLoading(false);
    }
  }

  async function loadAIQueue() {
    setAiLoading(true);
    setAiMessage("");
    try {
      const response = await fetch(`${apiBase(false)}/api/admin/review/items?limit=100`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error(response.status === 403 ? "AI review queue unavailable: admin imports are disabled." : `AI review queue failed: ${response.status}`);
      }
      const json = (await response.json()) as AIReviewQueueResponse;
      setAiItems(json.items);
      setAiTotalCount(json.total_count);
      setAiMessage(`${json.total_count} AI review item${json.total_count === 1 ? "" : "s"} in scope.`);
    } catch (error) {
      setAiItems([]);
      setAiTotalCount(0);
      setAiMessage(error instanceof Error ? error.message : "AI review queue unavailable.");
    } finally {
      setAiLoading(false);
    }
  }

  async function actOnAIItem(itemId: number, action: "approve" | "reject" | "block" | "publish") {
    setAiMessage("");
    try {
      const response = await fetch(`${apiBase(false)}/api/admin/review/items/${itemId}/${action}`, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-JTA-Admin-Token": token,
        },
        body: JSON.stringify({ actor: "prototype-admin", notes: `Prototype ${action} action.` }),
      });
      if (!response.ok) {
        throw new Error(`${action} failed with status ${response.status}`);
      }
      await loadAIQueue();
    } catch (error) {
      setAiMessage(error instanceof Error ? error.message : `${action} failed.`);
    }
  }

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <div className="kicker">Prototype admin</div>
          <h1>Evidence review queue</h1>
          <p className="meta">New court events, crime incidents, and legal sources should be reviewed before public display.</p>
        </div>
        <Link className="badge" href="/">Back to map</Link>
      </div>
      <section className="panel admin-review-panel">
        <h2>Access</h2>
        <p>
          This prototype endpoint is protected by <code>JTA_ENABLE_ADMIN_REVIEW</code> plus <code>X-JTA-Admin-Token</code>. It is not a replacement for real auth,
          roles, or audit policy.
        </p>
        <div className="admin-review-controls">
          <label className="field">
            <span>Admin review token</span>
            <input value={token} onChange={(event) => setToken(event.target.value)} placeholder="Token from JTA_ADMIN_REVIEW_TOKEN" type="password" />
          </label>
          <button className="primary-button" type="button" onClick={loadQueue} disabled={loading}>
            {loading ? "Loading..." : "Load queue"}
          </button>
        </div>
        <p className="admin-review-message">{message}</p>
      </section>
      <section className="panel">
        <h2>Evidence queue</h2>
        {items.length ? (
          <div className="review-queue-list">
            {items.map((item) => (
              <article className="review-queue-item" key={`${item.entity_type}-${item.database_id}`}>
                <div className="kicker">
                  {item.entity_type.replaceAll("_", " ")} · {formatStatus(item.review_status)}
                </div>
                <div className="row-title">{item.title || `${item.entity_type} ${item.entity_id}`}</div>
                <p className="meta">
                  Public: {item.public_visibility ? "yes" : "no"} · Source type: {item.source_type || "pending"} · Reviewed by{" "}
                  {item.reviewed_by || "pending"}
                </p>
                {item.review_notes ? <p>{item.review_notes}</p> : null}
                {item.correction_note ? <p>Correction: {item.correction_note}</p> : null}
                {item.dispute_note ? <p>Dispute: {item.dispute_note}</p> : null}
                <div className="admin-action-row">
                  <button type="button" onClick={() => actOnQueueItem(item.entity_type, item.entity_id, "approve")}>Approve</button>
                  <button type="button" onClick={() => actOnQueueItem(item.entity_type, item.entity_id, "reject")}>Reject</button>
                  <button type="button" onClick={() => actOnQueueItem(item.entity_type, item.entity_id, "remove")}>Remove</button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p>No queue records are loaded. The queue remains unavailable unless admin review is enabled.</p>
        )}
        {totalCount > items.length ? <p className="meta">{totalCount - items.length} additional records are outside the current page.</p> : null}
      </section>
      <section className="panel">
        <h2>Review history</h2>
        <p className="meta">Audit trail of all review decisions. Requires admin review to be enabled.</p>
        <button className="primary-button" type="button" onClick={loadHistory} disabled={historyLoading}>
          {historyLoading ? "Loading..." : "Load history"}
        </button>
        {historyMessage ? <p className="admin-review-message">{historyMessage}</p> : null}
        {history.length ? (
          <div className="review-queue-list">
            {history.map((entry) => (
              <article className="review-queue-item" key={entry.id}>
                <div className="kicker">
                  {entry.entity_type.replaceAll("_", " ")} #{entry.entity_id} · {formatStatus(entry.previous_status)} → {formatStatus(entry.new_status)}
                </div>
                <p className="meta">
                  Reviewed by {entry.reviewed_by || "unknown"} · {entry.reviewed_at ? entry.reviewed_at.slice(0, 19).replace("T", " ") : "date pending"} · Public: {entry.public_visibility ? "yes" : "no"}
                </p>
                {entry.notes ? <p>{entry.notes}</p> : null}
              </article>
            ))}
          </div>
        ) : null}
        {historyTotal > history.length ? <p className="meta">{historyTotal - history.length} additional audit records outside this page.</p> : null}
      </section>
      <section className="panel admin-review-panel">
        <h2>AI-assisted review items</h2>
        <p className="meta">AI drafts are evidence-clerk suggestions only. High-risk legal claims require human/admin approval before any public display.</p>
        <button className="primary-button" type="button" onClick={loadAIQueue} disabled={aiLoading}>
          {aiLoading ? "Loading..." : "Load AI review items"}
        </button>
        <p className="admin-review-message">{aiMessage}</p>
        {aiItems.length ? (
          <div className="review-queue-list">
            {aiItems.map((item) => (
              <article className="review-queue-item" key={`ai-${item.id}`}>
                <div className="kicker">
                  {item.record_type.replaceAll("_", " ")} · {formatStatus(item.status)} · {formatStatus(item.publish_recommendation)}
                </div>
                <div className="row-title">AI review item #{item.id}</div>
                <p className="meta">
                  Source quality: {item.source_quality} · Confidence: {Math.round(item.confidence * 100)}% · Privacy: {formatStatus(item.privacy_status)}
                </p>
                {item.source_quote ? <p><strong>Source quote:</strong> {item.source_quote}</p> : null}
                {item.neutral_summary ? <p><strong>Neutral summary:</strong> {item.neutral_summary}</p> : null}
                <pre className="payload-preview">{JSON.stringify(item.suggested_payload_json, null, 2)}</pre>
                <div className="admin-action-row">
                  <button type="button" onClick={() => actOnAIItem(item.id, "approve")}>Approve</button>
                  <button type="button" onClick={() => actOnAIItem(item.id, "reject")}>Reject</button>
                  <button type="button" onClick={() => actOnAIItem(item.id, "block")}>Block</button>
                  <button type="button" onClick={() => actOnAIItem(item.id, "publish")}>Publish draft</button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p>No AI review items are loaded. The queue remains unavailable unless admin imports are enabled.</p>
        )}
        {aiTotalCount > aiItems.length ? <p className="meta">{aiTotalCount - aiItems.length} additional AI records are outside the current page.</p> : null}
      </section>
    </main>
  );
}
