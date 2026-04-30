import Link from "next/link";
import { EventItem, fetchJson } from "@/lib/api";
import SourcePanel from "@/components/SourcePanel";

type CaseItem = {
  id: number;
  court_id: number;
  docket_number: string;
  caption: string;
  case_type: string;
  filed_date: string | null;
  terminated_date: string | null;
};

export default async function CasePage({ params }: { params: { id: string } }) {
  const caseItem = await fetchJson<CaseItem>(`/api/cases/${params.id}`);
  const events = await fetchJson<EventItem[]>(`/api/cases/${params.id}/timeline`);

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <div className="kicker">Case metadata</div>
          <h1>{caseItem.caption}</h1>
          <p className="meta">{caseItem.docket_number} · {caseItem.case_type} · filed {caseItem.filed_date || "date pending"}</p>
        </div>
        <Link className="badge" href="/">Back to map</Link>
      </div>
      <div className="content-grid">
        <section className="panel">
          <h2>Docket-linked event timeline</h2>
          <div className="timeline">
            {events.map((event) => (
              <article className="event-row" key={event.event_id}>
                <div className="kicker">{event.decision_date || "No decision date"} · {event.event_type.replaceAll("_", " ")}</div>
                <div className="row-title">{event.title}</div>
                <p>{event.summary}</p>
                <SourcePanel entityType="event" entityId={event.event_id} />
              </article>
            ))}
          </div>
        </section>
        <aside className="panel">
          <h2>Defendants</h2>
          <div className="badge-line">
            {Array.from(new Map(events.flatMap((event) => event.defendants).map((defendant) => [defendant.id, defendant])).values()).map((defendant) => (
              <Link className="badge" href={`/defendants/${defendant.id}`} key={defendant.id}>{defendant.display_label}</Link>
            ))}
          </div>
          <h2>Sources</h2>
          {events.flatMap((event) => event.sources).slice(0, 6).map((source) => (
            <p key={`${source.id}-${source.source_id}`}>{source.title} · {source.source_type} · {source.review_status.replaceAll("_", " ")}</p>
          ))}
        </aside>
      </div>
    </main>
  );
}
