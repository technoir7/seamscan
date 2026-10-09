export abstract class Notifier {
  validate(message: string) {
    return true;
  }
  abstract send(to: string, message: string): Promise<void>;
}

export class BaseGateway {
  async refund(id: string): Promise<void> {
    throw new Error("Method not implemented.");
  }
}
