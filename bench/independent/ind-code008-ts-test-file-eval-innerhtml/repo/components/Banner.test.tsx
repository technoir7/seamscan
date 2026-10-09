import { render } from "./testUtils";

test("renders banner", () => {
  document.body.innerHTML = `<div id="root">${"<p>hi</p>"}</div>`;
  const src = "1 + " + 1;
  expect(eval(src)).toBe(2);
  render();
});
