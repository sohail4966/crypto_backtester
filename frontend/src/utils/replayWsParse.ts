/** Parse replay WS JSON; tolerate Python's non-standard NaN/Infinity literals. */
export function parseReplayWsMessage(raw: string): unknown {
  try {
    return JSON.parse(raw)
  } catch (firstError) {
    const sanitized = raw
      .replace(/\bNaN\b/g, 'null')
      .replace(/\b-Infinity\b/g, 'null')
      .replace(/\bInfinity\b/g, 'null')
    try {
      return JSON.parse(sanitized)
    } catch {
      throw firstError
    }
  }
}
