function hideToast() {
  document.getElementById("toast").hidden = true;
}

function showToast(message) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.hidden = false;
  setTimeout(hideToast, 3000);
}
