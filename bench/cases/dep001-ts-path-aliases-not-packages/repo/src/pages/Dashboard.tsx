import { Card } from "@components/ui/card";
import { formatMoney } from "@shared/format";
import { useInvoices } from "hooks/useInvoices";
import logo from "~assets/logo.svg";
import { supabase } from "@/integrations/supabase/client";

export default function Dashboard() {
  const { data } = useInvoices(supabase);
  return (
    <Card>
      <img src={logo} alt="" />
      {formatMoney(data?.total ?? 0)}
    </Card>
  );
}
