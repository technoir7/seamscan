import { useQuery } from "@tanstack/react-query";

export const useInvoices = (client: any) =>
  useQuery({ queryKey: ["invoices"], queryFn: async () => (await client.from("invoices").select("*")).data });
