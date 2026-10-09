const BIDI = /[\u202a-\u202e\u2066-\u2069]/g;
const ZWSP = "\u200b";

export function clean(s: string) {
  return s.replace(BIDI, "").split(ZWSP).join("");
}
