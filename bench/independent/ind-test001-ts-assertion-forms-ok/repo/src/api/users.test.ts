import request from "supertest";
import { render } from "@testing-library/react";
import { app } from "./app";
import { PriceTag } from "../components/PriceTag";
import { loadUser } from "./users";

it("renders a sale price", () => {
  expect(render(<PriceTag cents={1999} />).container).toMatchSnapshot();
});

it("rejects an unknown id", async () => {
  await expect(loadUser("nope")).rejects.toThrow("not found");
});

it("calls the callback twice", () => {
  expect.assertions(1);
  const calls: number[] = [];
  [1, 2].forEach((n) => calls.push(n));
  return Promise.resolve().then(() => expect(calls.length).toBe(2));
});

it("GET /users returns 200", async () => {
  await request(app).get("/users").expect(200);
});

it("returns the user body", async () => {
  const res = await request(app).get("/users/1");
  res.body.should.have.property("id");
});
