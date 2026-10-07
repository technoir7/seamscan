export async function shipLogs(entry: Record<string, unknown>) {
  if (process.env.ELK_URL) {
    // ELK output is best effort; the request must not wait for it
    fetch(process.env.ELK_URL, { method: "POST", body: JSON.stringify(entry) }).catch(() => {
      // Ignore ELK errors: the entry is also written to stdout
    });
  }
}

export async function titleFor(chatId: string, generate: () => Promise<string>) {
  try {
    return await generate();
  } catch {
    /* non-fatal: the chat keeps its default title */
  }
}
