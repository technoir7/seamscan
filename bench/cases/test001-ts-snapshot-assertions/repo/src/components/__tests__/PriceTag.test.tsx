import { render } from "@testing-library/react";
import { expect, it } from "vitest";
import { formatPrice } from "../../lib/format";
import { PriceTag } from "../PriceTag";

it("renders a sale price", () => {
  const { container } = render(<PriceTag cents={1999} wasCents={2999} />);
  expect(container.firstChild).toMatchSnapshot();
});

it("formats euros", () => {
  expect(formatPrice(1999, "EUR")).toMatchInlineSnapshot(`"19,99 €"`);
});

it("rejects a negative amount", async () => {
  expect.assertions(1);
  await expect(Promise.resolve().then(() => formatPrice(-1, "USD"))).rejects.toThrow(
    "amount must be positive",
  );
});
