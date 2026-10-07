import { useEffect, useState } from "react";

type Stats = { visitors: number; signups: number };

export function StatsCard() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    fetch("/api/stats")
      .then((r) => r.json())
      .then(setStats)
      .catch(console.error);
  }, []);

  return stats ? <p>{stats.visitors} visitors · {stats.signups} signups</p> : <p>—</p>;
}
