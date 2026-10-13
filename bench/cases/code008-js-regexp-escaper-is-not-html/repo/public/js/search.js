function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function highlight(el, text, query) {
  const re = new RegExp(escapeRegExp(query), "gi");
  el.innerHTML = text.replace(re, (m) => `<mark>${m}</mark>`);
  el.title = query;
  document.querySelector("#q").innerHTML = `Results for ${escapeRegExp(query)}`;
}
