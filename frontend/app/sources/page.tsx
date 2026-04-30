import Link from "next/link";
import { fetchJson } from "@/lib/api";
import SourcePanel from "@/components/SourcePanel";

type Source = {
  id: number;
  source_id: string;
  source_type: string;
  title: string;
  url: string;
  source_quality: string;
  verified_flag: boolean;
  review_status: string;
};

export default async function SourcesPage() {
  const sources = await fetchJson<Source[]>("/api/sources");

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <div className="kicker">Source list</div>
          <h1>Legal sources</h1>
          <p className="meta">News remains secondary context and unmatched source review is a placeholder queue.</p>
        </div>
        <Link className="badge" href="/">Back to map</Link>
      </div>
      <table className="source-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Type</th>
            <th>Quality</th>
            <th>Verified</th>
            <th>Review</th>
            <th>Evidence</th>
          </tr>
        </thead>
        <tbody>
          {sources.map((source) => (
            <tr key={source.id}>
              <td><a href={source.url}>{source.title}</a></td>
              <td>{source.source_type}</td>
              <td>{source.source_quality}</td>
              <td>{source.verified_flag ? "yes" : "no"}</td>
              <td>{source.review_status.replaceAll("_", " ")}</td>
              <td><SourcePanel entityType="source" entityId={source.source_id} compact /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <section className="panel mt-md">
        <h2>Unmatched news/source queue</h2>
        <p>Placeholder only. Secondary context cannot create outcomes or primary decision records.</p>
      </section>
    </main>
  );
}
