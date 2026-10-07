import type { PaymentProvider, Charge } from "./types";

export class PayPalProvider implements PaymentProvider {
  constructor(private readonly clientId: string) {}

  async charge(amountCents: number, currency: string): Promise<Charge> {
    const res = await fetch("https://api-m.paypal.com/v2/checkout/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent: "CAPTURE", amount: { amountCents, currency } }),
    });
    return (await res.json()) as Charge;
  }

  async refund(chargeId: string): Promise<void> {
    throw new Error("Method not implemented.");
  }
}
