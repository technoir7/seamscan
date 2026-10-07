import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Plans } from "./Plans";

describe("Plans", () => {
  it("renders the plans section", () => {
    render(<Plans />);
    expect(screen.getByRole("region", { name: "Plans" })).toBeInTheDocument();
  });

  it.todo("highlights the current plan");
  it.todo("disables downgrade during a trial");
});
