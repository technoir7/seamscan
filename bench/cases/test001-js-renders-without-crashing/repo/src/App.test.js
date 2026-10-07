import React from "react";
import { createRoot } from "react-dom/client";
import { act } from "react";
import App from "./App";
import { parseQuery } from "./lib/query";

it("renders without crashing", () => {
  const div = document.createElement("div");
  act(() => {
    createRoot(div).render(<App />);
  });
});

it("does not throw on an empty query string", () => {
  parseQuery("");
});
