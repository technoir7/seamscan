import { PaymentGateway } from "./gateway";

export class PaypalGateway implements PaymentGateway {
  async charge(amount: number, token: string): Promise<string> {
    return `pp_${token}_${amount}`;
  }

  async refund(chargeId: string): Promise<void> {
    throw new Error("Method not implemented.");
  }
}
