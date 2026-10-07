import "./style.css";

type Todo = { id: number; text: string; done: boolean };

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const list = document.querySelector<HTMLUListElement>("#todos")!;

export function render(todos: Todo[]) {
  list.innerHTML = todos
    .map((t) => `<li class="${t.done ? "done" : ""}">${escapeHtml(t.text)}</li>`)
    .join("");
}
