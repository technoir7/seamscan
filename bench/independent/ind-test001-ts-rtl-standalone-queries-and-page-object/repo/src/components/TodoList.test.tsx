import { render, screen } from "@testing-library/react";
import { TodoList } from "./TodoList";

test("shows the empty state", () => {
  render(<TodoList todos={[]} />);
  screen.getByText("Nothing to do. Enjoy your day!");
});

test("shows a loaded todo", async () => {
  render(<TodoList todos={[{ id: 1, title: "Buy milk" }]} />);
  await screen.findByText("Buy milk");
});
