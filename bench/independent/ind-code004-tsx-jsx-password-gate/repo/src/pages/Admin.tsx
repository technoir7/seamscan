import { useState } from "react";
import { AdminPanel } from "../components/AdminPanel";

export default function Admin() {
  const [password, setPassword] = useState("");
  return (
    <div>
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      {password === "hunter2-admin" && <AdminPanel />}
    </div>
  );
}
