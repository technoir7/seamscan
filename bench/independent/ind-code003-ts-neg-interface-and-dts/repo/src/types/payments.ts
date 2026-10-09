export interface PaymentGateway {
  charge(amount: number, token: string): Promise<string>;
  refund(chargeId: string): Promise<void>;
  validate(input: unknown): boolean;
}

export declare function verifySignature(payload: string, sig: string): boolean;
