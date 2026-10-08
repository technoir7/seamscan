import { useEffect, useState } from "react";
import { fetchRepoStats } from "../services/github";

export default function RepoCard({ owner, repo }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchRepoStats(owner, repo).then(setStats);
  }, [owner, repo]);

  if (!stats) return <p>Loading…</p>;
  return (
    <div className="card">
      <h3>{owner}/{repo}</h3>
      <p>★ {stats.stars} · forks {stats.forks}</p>
      <p>Top: {stats.topContributors.join(", ")}</p>
    </div>
  );
}
