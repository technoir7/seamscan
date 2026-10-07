import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { NewsletterForm } from "./NewsletterForm";

test("submits the email to the subscribe endpoint", async () => {
  const onSubscribe = vi.fn().mockResolvedValue({ ok: true });
  render(<NewsletterForm onSubscribe={onSubscribe} />);

  await userEvent.type(screen.getByLabelText("Email"), "ada@example.com");
  await userEvent.click(screen.getByRole("button", { name: "Subscribe" }));
});

test("disables the button while submitting", async () => {
  render(<NewsletterForm onSubscribe={() => new Promise(() => {})} />);
  await userEvent.type(screen.getByLabelText("Email"), "ada@example.com");
  await userEvent.click(screen.getByRole("button", { name: "Subscribe" }));
  expect(screen.getByRole("button", { name: "Subscribing…" })).toBeDisabled();
});
