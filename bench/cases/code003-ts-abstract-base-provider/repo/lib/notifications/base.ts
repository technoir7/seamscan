export abstract class Notifier {
  abstract send(userId: string, message: string): Promise<void>;

  validate(message: string): boolean {
    return true;
  }

  async sendBatch(userIds: string[], message: string): Promise<void> {
    throw new Error("Not implemented");
  }
}

export class EmailNotifier extends Notifier {
  async send(userId: string, message: string) {
    await fetch("/api/email", { method: "POST", body: JSON.stringify({ userId, message }) });
  }
}
