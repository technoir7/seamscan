import { useEffect, useState } from "react";

export default function EmbedPreview() {
  const [data, setData] = useState<unknown>(null);
  const target = new URLSearchParams(window.location.search).get("src");

  useEffect(() => {
    if (!target) return;
    fetch(target)
      .then((r) => r.json())
      .then(setData);
  }, [target]);

  return <pre className="text-xs">{JSON.stringify(data, null, 2)}</pre>;
}
