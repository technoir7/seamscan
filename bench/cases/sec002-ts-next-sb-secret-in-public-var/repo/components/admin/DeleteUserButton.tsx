"use client";

import { createClient } from "@supabase/supabase-js";
import { useTransition } from "react";

const admin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_SECRET_KEY!,
);

export function DeleteUserButton({ userId }: { userId: string }) {
  const [pending, start] = useTransition();
  return (
    <button
      disabled={pending}
      onClick={() => start(async () => void (await admin.auth.admin.deleteUser(userId)))}
    >
      {pending ? "Deleting..." : "Delete user"}
    </button>
  );
}
