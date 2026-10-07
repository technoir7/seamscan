import axios from "axios";

type Plan = "free" | "pro";

export function exhaustiveCheck(_value: never): void {}

export function priceFor(plan: Plan): number {
  switch (plan) {
    case "free":
      return 0;
    case "pro":
      return 20;
    default:
      exhaustiveCheck(plan);
      return 0;
  }
}

export const api = axios.create({
  baseURL: process.env.API_URL,
  validateStatus: () => true,
});
