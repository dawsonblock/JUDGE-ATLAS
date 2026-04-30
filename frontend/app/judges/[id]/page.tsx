import Link from "next/link";
import { EventItem, fetchJson } from "@/lib/api";
import SourcePanel from "@/components/SourcePanel";

type Judge = { id: number; name: string; court_id: number | null };

export default async function JudgePage({ params }: { params: { id: string } }) {
  const judge = await fetchJson<Judge>(`/api/judges/${params.id}`);
  const events = await fetchJson<EventItem[]>(`/api/judges/${params.id}/events`);
  const repeatCount = events.filter((event) => event.repeat_offender_indicator).length;

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <div className="kicker">Judge profile</div>
          <h1>{judge.name}</h1>
          <p className="meta">Linked legal event timeline and repeat-offender indicator rollup.</p>
        </div>
        <Link className="badge" href="/">Back to map</Link>
      </div>
      <div className="content-grid">
        <section className="panel">
          <h2>Event timeline</h2>
          <div className="timeline">
            {events.map((event) => (
              <article className="event-row" key={event.event_id}>
                <div className="kicker">{event.decision_date || "No decision date"} · {event.event_type.replaceAll("_", " ")}</div>
                <Link className="row-title" href={`/cases/${event.case_id}`}>{event.title}</Link>
                <div className="meta">{event.outcome_status || "verified outcome recorded"}</div>
                <SourcePanel entityType="event" entityId={event.event_id} />
              </article>
            ))}
          </div>
        </section>
        <aside className="panel">
          <h2>Rollup</h2>
          <p>{events.length} linked legal events</p>
          <p>{repeatCount} with repeat-offender indicators</p>
          <p>Map association is by courthouse or court jurisdiction, not personal location.</p>
        </aside>
      </div>
    </main>
  );
}
