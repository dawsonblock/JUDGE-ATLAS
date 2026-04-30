import Link from "next/link";
import { EventItem, fetchJson } from "@/lib/api";
import SourcePanel from "@/components/SourcePanel";

type Defendant = {
  id: number;
  anonymized_id: string;
  display_label: string;
  warning: string;
};

export default async function DefendantPage({ params }: { params: { id: string } }) {
  const defendant = await fetchJson<Defendant>(`/api/defendants/${params.id}`);
  const events = await fetchJson<EventItem[]>(`/api/defendants/${params.id}/timeline`);

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <div className="kicker">Anonymized defendant profile</div>
          <h1>{defendant.display_label}</h1>
          <p className="meta">{defendant.warning}</p>
        </div>
        <Link className="badge" href="/">Back to map</Link>
      </div>
      <div className="content-grid">
        <section className="panel">
          <h2>Linked decisions</h2>
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
          <h2>Verified outcomes</h2>
          {events.map((event) => (
            <p key={event.event_id}>{event.outcomes.length ? event.outcomes.map((outcome) => outcome.summary).join(" ") : event.outcome_status}</p>
          ))}
        </aside>
      </div>
    </main>
  );
}
