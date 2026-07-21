const registerUrl = "http://127.0.0.1:8100/register";

function addSignUpLink() {
  if (document.getElementById("local-rag-sign-up")) return true;
  const submit = document.querySelector('button[type="submit"]');
  if (!submit) return false;
  const link = document.createElement("a");
  link.id = "local-rag-sign-up";
  link.className = "auth-secondary-button";
  link.href = registerUrl;
  link.textContent = "Sign up";
  submit.insertAdjacentElement("afterend", link);
  return true;
}

const observer = new MutationObserver(() => {
  if (addSignUpLink()) observer.disconnect();
});
observer.observe(document.body, { childList: true, subtree: true });
addSignUpLink();
