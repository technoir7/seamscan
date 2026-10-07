"use client";

import Link from "next/link";
import { jwtDecode } from "jwt-decode";
import { useAuth } from "@/hooks/useAuth";

type Claims = { name: string; role: "admin" | "member" };

export function UserMenu() {
  const { token } = useAuth();
  if (!token) return <Link href="/login">Sign in</Link>;
  const { name, role } = jwtDecode<Claims>(token);
  return (
    <nav className="flex items-center gap-4">
      <span className="text-sm text-muted-foreground">{name}</span>
      {role === "admin" && <Link href="/admin">Admin</Link>}
    </nav>
  );
}
