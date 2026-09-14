"use client";

const USER_LLM_KEY = "databoom-user-llm-key";

export function getSessionLlmKey() {
  return window.sessionStorage.getItem(USER_LLM_KEY) ?? "";
}

export function setSessionLlmKey(value: string) {
  const normalized = value.trim();
  if (normalized) {
    window.sessionStorage.setItem(USER_LLM_KEY, normalized);
  } else {
    window.sessionStorage.removeItem(USER_LLM_KEY);
  }
}
