const input = document.querySelector("#search");
const results = document.querySelector("#results");
const heading = document.querySelector("#query");

input.addEventListener("input", async () => {
  const res = await fetch(`/api/search?q=${encodeURIComponent(input.value)}`);
  const items = await res.json();
  heading.innerHTML = `Results for <b>${input.value}</b>`;
  results.innerHTML = items
    .map((item) => `<li><a href="/p/${item.slug}">${item.title}</a></li>`)
    .join("");
});
