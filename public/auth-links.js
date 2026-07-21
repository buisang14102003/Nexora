const registerUrl = "http://127.0.0.1:8100/register";

function sendWorkspaceCommand(name) {
  const input = document.querySelector("textarea") || document.querySelector('input[placeholder*="message" i]');
  if (!input) return;
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set
    || Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  setter?.call(input, `/create-workspace ${name}`);
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.closest("form")?.requestSubmit();
}

function addWorkspaceButton() {
  if (location.pathname === "/login" || document.getElementById("local-rag-workspace-create")) return;
  const button = document.createElement("button");
  button.id = "local-rag-workspace-create";
  button.type = "button";
  button.textContent = "+ Tạo workspace";
  button.addEventListener("click", () => {
    const name = window.prompt("Tên workspace mới:");
    if (name?.trim()) sendWorkspaceCommand(name.trim());
  });
  (document.querySelector('[data-testid="sidebar"]') || document.querySelector("aside") || document.body)
    .append(button);
}

function addSignUpLink() {
  if (document.getElementById("local-rag-sign-up")) return true;
  const submit = document.querySelector('button[type="submit"]');
  if (!submit) return false;
  const link = document.createElement("a");
  link.id = "local-rag-sign-up";
  link.className = "auth-secondary-button";
  link.href = registerUrl;
  link.textContent = "Tạo tài khoản";
  submit.insertAdjacentElement("afterend", link);
  return true;
}

const observer = new MutationObserver(() => {
  addSignUpLink();
  addWorkspaceButton();
});
observer.observe(document.body, { childList: true, subtree: true });
addSignUpLink();
addWorkspaceButton();
