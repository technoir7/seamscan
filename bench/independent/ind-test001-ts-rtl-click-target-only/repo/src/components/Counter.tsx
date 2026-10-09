import { useState } from "react";
export function Counter() {
  const [n, setN] = useState(0);
  return <div><span data-testid="count">{n}</span><button onClick={() => setN(n + 1)}>+</button></div>;
}
