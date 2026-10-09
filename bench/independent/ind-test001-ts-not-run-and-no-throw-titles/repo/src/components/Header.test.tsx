import { render } from "@testing-library/react";
import { Header } from "./Header";
import { parseNav } from "./nav";

describe("Header", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders without crashing", () => {
    render(<Header />);
  });

  it("does not throw on empty input", () => {
    parseNav([]);
  });

  it.todo("downgrades at the end of the period");

  it.skip("collapses on mobile", () => {
    render(<Header />);
  });

  xit("shows a banner for admins", () => {
    render(<Header admin />);
  });
});
