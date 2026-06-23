export function readJsonPref<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) as T : fallback
  } catch {
    return fallback
  }
}

export function writeJsonPref(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Local preferences are best-effort only.
  }
}

export function removePref(key: string) {
  localStorage.removeItem(key)
}
