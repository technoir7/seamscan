import escapeHtml from "escape-html";

const notesEl = document.getElementById("notes");
const countEl = document.getElementById("count");

export async function loadNotes() {
  const res = await fetch("/api/notes");
  const notes = await res.json();
  countEl.innerHTML = `<span class="badge">${notes.length}</span>`;
  notesEl.innerHTML = notes
    .map((n, i) => `<li id="note-${i}"><h3>${escapeHtml(n.title)}</h3><p>${escapeHtml(n.body)}</p></li>`)
    .join("");
}
