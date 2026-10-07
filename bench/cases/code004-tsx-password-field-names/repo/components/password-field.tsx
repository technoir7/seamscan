"use client";

import { useState } from "react";

export function PasswordField({ name, strength }: { name: string; strength: "weak" | "ok" | "strong" }) {
  const [showPassword, setShowPassword] = useState(false);
  const inputType = showPassword ? "text" : "password";
  const passwordStrength = strength;

  return (
    <div>
      <input name={name} type={inputType} autoComplete={name === "password" ? "current-password" : "new-password"} />
      {inputType === "password" && <button onClick={() => setShowPassword(true)}>Show</button>}
      {passwordStrength === "weak" && <p>Try a longer password.</p>}
    </div>
  );
}
