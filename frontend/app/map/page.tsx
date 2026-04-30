import Link from "next/link";
import JudgeNorthAmericaMapClient from "@/components/JudgeNorthAmericaMapClient";

export default function MapPage() {
  return (
    <main className="page map-page">
      <div className="page-header">
        <div>
          <div className="kicker">Court-event map</div>
          <h1>North America Legal Event Map</h1>
          <p className="meta">Court events are plotted by courthouse or court jurisdiction location. Recent crime incidents are a separate reported-incident context layer using generalized public areas. Defendant private locations are intentionally excluded.</p>
        </div>
        <Link className="badge" href="/">Back to dashboard</Link>
      </div>
      <JudgeNorthAmericaMapClient />
    </main>
  );
}
