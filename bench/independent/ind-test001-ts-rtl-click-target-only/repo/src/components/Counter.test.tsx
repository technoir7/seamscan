import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Counter } from "./Counter";

describe("Counter", () => {
  it("starts at zero", () => {
    render(<Counter />);
    expect(screen.getByTestId("count").textContent).toBe("0");
  });

  it("increments when the plus button is pressed", async () => {
    render(<Counter />);
    await userEvent.click(screen.getByRole("button", { name: "+" }));
  });
});
