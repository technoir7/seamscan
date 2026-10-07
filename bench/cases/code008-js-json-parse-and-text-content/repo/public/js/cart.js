const list = document.getElementById("cart-items");
const total = document.getElementById("cart-total");

function renderCart() {
  const cart = JSON.parse(localStorage.getItem("cart") || "[]");
  list.innerHTML = "";
  for (const item of cart) {
    const li = document.createElement("li");
    li.textContent = `${item.name} x ${item.qty}`;
    list.appendChild(li);
  }
  total.innerHTML = `<strong>${cart.length}</strong> items`;
}

window.addEventListener("storage", renderCart);
renderCart();
