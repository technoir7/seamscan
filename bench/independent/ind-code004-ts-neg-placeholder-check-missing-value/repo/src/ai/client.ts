export function makeClient(apiKey?: string) {
  if (!apiKey || apiKey === "test-key") return mockClient();
  return realClient(apiKey);
}

export function configured(key?: string) {
  return key && key !== "your-key-here";
}

declare function mockClient(): unknown;
declare function realClient(k: string): unknown;
