import { render, screen, waitForElementToBeRemoved } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TodoList } from "./TodoList";

test("shows the empty state", () => {
  render(<TodoList todos={[]} />);
  screen.getByText("Nothing to do. Enjoy your day!");
});

test("loads todos from the server", async () => {
  render(<TodoList />);
  await waitForElementToBeRemoved(() => screen.queryByText("Loading…"));
  await screen.findByRole("listitem", { name: "Buy milk" });
});

test("removes a todo", async () => {
  const { getByRole, queryByText } = render(<TodoList todos={[{ id: 1, title: "Buy milk" }]} />);
  await userEvent.click(getByRole("button", { name: "Delete Buy milk" }));
  expect(queryByText("Buy milk")).toBeNull();
});
