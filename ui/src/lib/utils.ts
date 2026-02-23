import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;

  const cookies = document.cookie.split(";");
  for (let i = 0; i < cookies.length; i++) {
    const cookie = cookies[i].trim();
    if (cookie.startsWith(name + "=")) {
      return cookie.substring(name.length + 1);
    }
  }
  return null;
}

export function setCookie(
  name: string,
  value: string,
  maxAgeSeconds?: number
): void {
  if (typeof document === "undefined") return;

  const maxAge =
    typeof maxAgeSeconds === "number"
      ? `; max-age=${Math.floor(maxAgeSeconds)}`
      : "";

  document.cookie = `${name}=${value}${maxAge}; path=/`;
}

export function removeCookie(name: string): void {
  if (typeof document === "undefined") return;

  setCookie(name, "", -1);
}
