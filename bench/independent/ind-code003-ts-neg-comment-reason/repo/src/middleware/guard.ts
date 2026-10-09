export function authorizeRequest() {
  // Always run the middleware above, which redirects itself
  return true;
}
