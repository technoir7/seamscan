"use client";
import { jwtDecode } from "jwt-decode";
import { useAuthToken } from "@/hooks/useAuthToken";

interface Claims {
  name: string;
  email: string;
  role: string;
}

export default function Greeting() {
  const token = useAuthToken();
  if (!token) return null;
  const { name, role } = jwtDecode<Claims>(token);
  return <p>Hi {name}{role === "admin" ? " (admin tools in the menu)" : ""}</p>;
}
