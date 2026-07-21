const TOKEN_KEY = "local-rag-access-token";

export function readToken(): string | null {
  return window.sessionStorage.getItem(TOKEN_KEY);
}

export function saveToken(token: string): void {
  window.sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.sessionStorage.removeItem(TOKEN_KEY);
}
