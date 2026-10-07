// Values with a public prefix are inlined into the browser bundle by Vite and Next.js,
// so a literal default here exposes nothing that the variable itself wouldn't.
export const config = {
  mapsKey: import.meta.env.VITE_MAPBOX_PUBLIC_TOKEN ?? "demo-token",
  analyticsKey: import.meta.env.VITE_POSTHOG_KEY || "phc_local_dev",
  siteToken: process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY ?? "1x00000000000000000000AA",
  expoKey: process.env.EXPO_PUBLIC_REVENUECAT_KEY ?? "appl_dev",
  craKey: process.env.REACT_APP_SEGMENT_WRITE_KEY || "dev-write-key",
};
