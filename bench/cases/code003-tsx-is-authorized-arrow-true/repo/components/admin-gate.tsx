"use client";

import type { ReactNode } from "react";
import { useUser } from "@/hooks/use-user";

const isAuthorized = (user: { role?: string } | null) => true;

export function AdminGate({ children }: { children: ReactNode }) {
  const user = useUser();
  if (!isAuthorized(user)) {
    return <p className="text-sm text-muted-foreground">You don't have access to this page.</p>;
  }
  return <>{children}</>;
}
