async function refreshCard(id) {
  const res = await fetch(`/cards/${id}/fragment`);
  const fragment = await res.text();
  document.getElementById("card-" + id).outerHTML = fragment;
}
