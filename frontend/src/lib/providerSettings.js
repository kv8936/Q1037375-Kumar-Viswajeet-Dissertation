import { browser } from "$app/environment";

const STORAGE_KEY = "hazard-chatbot-provider-settings";

export const PROVIDERS = {
  local: "local",
  openai: "openai",
  anthropic: "anthropic",
};

export const defaultProviderSettings = {
  provider: PROVIDERS.local,
  remember: false,
  openaiApiKey: "",
  anthropicApiKey: "",
};

export function normalizeProviderSettings(input = {}) {
  const provider = Object.values(PROVIDERS).includes(input.provider)
    ? input.provider
    : PROVIDERS.local;

  return {
    provider,
    remember: Boolean(input.remember),
    openaiApiKey: String(input.openaiApiKey ?? "").trim(),
    anthropicApiKey: String(input.anthropicApiKey ?? "").trim(),
  };
}

function readStorage(storage) {
  if (!browser || !storage) {
    return null;
  }

  const raw = storage.getItem(STORAGE_KEY);

  if (!raw) {
    return null;
  }

  try {
    return normalizeProviderSettings(JSON.parse(raw));
  } catch {
    return null;
  }
}

function writeStorage(storage, settings) {
  if (!browser || !storage) {
    return;
  }

  storage.setItem(
    STORAGE_KEY,
    JSON.stringify(normalizeProviderSettings(settings)),
  );
}

export function loadProviderSettings() {
  if (!browser) {
    return { ...defaultProviderSettings };
  }

  return (
    readStorage(window.localStorage) ??
    readStorage(window.sessionStorage) ?? { ...defaultProviderSettings }
  );
}

export function saveProviderSettings(settings) {
  if (!browser) {
    return;
  }

  const normalized = normalizeProviderSettings(settings);

  if (normalized.remember) {
    writeStorage(window.localStorage, normalized);
    window.sessionStorage.removeItem(STORAGE_KEY);
  } else {
    writeStorage(window.sessionStorage, normalized);
    window.localStorage.removeItem(STORAGE_KEY);
  }
}

export function clearProviderSettings() {
  if (!browser) {
    return;
  }

  window.localStorage.removeItem(STORAGE_KEY);
  window.sessionStorage.removeItem(STORAGE_KEY);
}

export function getActiveProviderKey(settings) {
  const normalized = normalizeProviderSettings(settings);

  if (normalized.provider === PROVIDERS.openai) {
    return normalized.openaiApiKey;
  }

  if (normalized.provider === PROVIDERS.anthropic) {
    return normalized.anthropicApiKey;
  }

  return "";
}

export function getProviderLabel(provider, t = (value) => value) {
  const normalized = Object.values(PROVIDERS).includes(provider)
    ? provider
    : PROVIDERS.local;

  if (normalized === PROVIDERS.openai) {
    return t("provider_openai");
  }

  if (normalized === PROVIDERS.anthropic) {
    return t("provider_anthropic");
  }

  return t("provider_local");
}

export function maskApiKey(value) {
  const key = String(value ?? "").trim();

  if (!key) {
    return "";
  }

  if (key.length <= 8) {
    return `•••• ${key}`;
  }

  return `${key.slice(0, 4)}••••${key.slice(-4)}`;
}
