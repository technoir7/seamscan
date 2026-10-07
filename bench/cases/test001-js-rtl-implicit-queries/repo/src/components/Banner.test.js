import { render, screen } from "@testing-library/react";
import { Banner } from "./Banner";

it("shows the maintenance message", () => {
  const { getByText } = render(<Banner status="maintenance" />);
  getByText("We'll be back shortly.");
});

it("links to the status page", async () => {
  render(<Banner status="degraded" />);
  await screen.findByRole("link", { name: "View status page" });
});
