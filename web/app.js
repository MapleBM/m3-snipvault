const form = document.getElementById("new");
const link = document.getElementById("link");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = new URLSearchParams(new FormData(form));
  const res = await fetch("/api/snips", { method: "POST", body, headers: { "Content-Type": "application/x-www-form-urlencoded" }});
  const data = await res.json();
  link.textContent = `Share: ${location.origin}/s/${data.id}`;
  link.onclick = () => location.assign(`/s/${data.id}`);
});
