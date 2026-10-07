import { useState } from "react";

export function VaultLock({ onUnlock }: { onUnlock: () => void }) {
  const [pin, setPin] = useState("");
  const [error, setError] = useState(false);

  function submit() {
    if (pin === "4821") {
      onUnlock();
    } else {
      setError(true);
    }
  }

  return (
    <div>
      <input inputMode="numeric" value={pin} onChange={(e) => setPin(e.target.value)} />
      <button onClick={submit}>Unlock</button>
      {error && <p>Wrong PIN</p>}
    </div>
  );
}
