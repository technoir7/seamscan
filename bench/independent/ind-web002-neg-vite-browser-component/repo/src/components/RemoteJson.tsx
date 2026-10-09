import { useEffect, useState } from "react";

export function RemoteJson() {
  const [data, setData] = useState<unknown>(null);
  useEffect(() => {
    const url = new URLSearchParams(window.location.search).get("url");
    if (url) fetch(url).then((r) => r.json()).then(setData);
  }, []);
  return <pre>{JSON.stringify(data, null, 2)}</pre>;
}
