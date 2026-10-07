export function assertCredentials({ password, apiKey, token }) {
  if (typeof password !== "string" || password.length < 12) {
    throw new TypeError("password must be a string of at least 12 characters");
  }
  if (typeof apiKey === "undefined") {
    throw new TypeError("apiKey is required");
  }
  if (typeof token !== "string") {
    throw new TypeError("token must be a string");
  }
}
