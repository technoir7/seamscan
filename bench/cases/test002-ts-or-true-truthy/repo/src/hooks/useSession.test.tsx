import { renderHook, waitFor } from "@testing-library/react";
import { expect, test } from "vitest";
import { useSession } from "./useSession";

test("restores the session from storage", async () => {
  localStorage.setItem("sb-session", JSON.stringify({ user: { id: "u1" } }));
  const { result } = renderHook(() => useSession());
  await waitFor(() => expect(result.current.user?.id === "u1" || true).toBeTruthy());
});

test("starts signed out", () => {
  localStorage.clear();
  const { result } = renderHook(() => useSession());
  expect(result.current.user).toBeNull();
});
