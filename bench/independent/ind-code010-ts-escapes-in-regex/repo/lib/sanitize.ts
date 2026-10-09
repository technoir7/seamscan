const BIDI = /[‪-‮⁦-⁩]/g;
const ZWSP = "​";

export function clean(s: string) {
  return s.replace(BIDI, "").split(ZWSP).join("");
}
