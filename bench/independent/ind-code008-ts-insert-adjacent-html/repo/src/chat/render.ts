export function appendMessage(list: HTMLElement, msg: { author: string; html: string }) {
  list.insertAdjacentHTML("beforeend", `<div class="msg"><b>${msg.author}</b> ${msg.html}</div>`);
  list.scrollTop = list.scrollHeight;
}
