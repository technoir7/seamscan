const form = document.querySelector("#login");

form.addEventListener("submit", (e) => {
  e.preventDefault();
  if (form.password.value === "letmein") {
    window.location.href = "/app";
  } else {
    alert("wrong password");
  }
});
