import Link from "next/link";
import { fetchJson } from "@/lib/api";

type JudgeSummary = {
  id: number;
  name: string;
  court_id: number | null;
  cl_person_id: string | null;
  public_event_count: number;
};

export default async function JudgesPage() {
  let judges: JudgeSummary[] = [];
  let fetchError: string | null = null;
  try {
    judges = await fetchJson<JudgeSummary[]>("/api/judges");
  } catch (err) {
    fetchError = err instanceof Error ? err.message : "Failed to load judges.";
  }

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <div className="kicker">Directory</div>
          <h1>Judges</h1>
          <p className="meta">
            Judge profiles show linked legal event timelines and repeat-offender
            indicator rollups. Map dots use courthouse locations — never personal
            addresses.
          </p>
        </div>
      </div>
      {fetchError ? (
        <div className="error-banner">{fetchError}</div>
      ) : judges.length === 0 ? (
        <div className="panel mt-md">
          <p>No judges are linked to any events yet.</p>
        </div>
      ) : (
        <table className="source-table mt-md">
          <thead>
            <tr>
              <th>Name</th>
              <th>CL Person ID</th>
              <th>Events</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {judges.map((judge) => (
              <tr key={judge.id}>
                <td>
                  <Link href={`/judges/${judge.id}`} className="row-link">
                    {judge.name}
                  </Link>
                </td>
                <td className="meta">{judge.cl_person_id ?? "—"}</td>
                <td>{judge.public_event_count}</td>
                <td>
                  <Link className="badge" href={`/judges/${judge.id}`}>
                    View profile →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
