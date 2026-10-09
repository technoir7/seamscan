"use client";

export function ping() {
  return fetch("/api/ping", {
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Credentials": "true",
    },
  });
}
