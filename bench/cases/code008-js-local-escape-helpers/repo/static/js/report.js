function esc(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function _pbEsc(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

export function renderHistory(list, items) {
  list.innerHTML = items
    .map((h) => `<div class="item" data-id="${esc(h.jobId)}">${esc(h.title)}</div>`)
    .join("");
}

export function renderPlaybook(el, pb) {
  el.innerHTML = `<h3>${_pbEsc(pb.name)}</h3><p>${_pbEsc(pb.summary)}</p>`;
}
