const BIDI_CONTROLS = /[\u202A-\u202E\u2066-\u2069\u200E\u200F]/g;
const ZERO_WIDTH = new RegExp("[\u200B-\u200D\u2060\uFEFF]", "g");

export function sanitizeDisplayName(name) {
  return name.replace(BIDI_CONTROLS, "").replace(ZERO_WIDTH, "").trim();
}
