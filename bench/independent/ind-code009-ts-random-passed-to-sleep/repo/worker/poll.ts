import { sleep } from "./sleep";

export async function pollLoop(run: () => Promise<void>) {
  for (;;) {
    await run();
    const jitter = Math.random() * 1000;
    await sleep(jitter);
  }
}
