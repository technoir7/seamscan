import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { generatePdf } from "react-pdf-invoice-generator";

export function InvoiceDownload({ invoiceId }: { invoiceId: string }) {
  const { toast } = useToast();

  const handleDownload = async () => {
    const blob = await generatePdf({ invoiceId, template: "modern" });
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
    toast({ title: "Invoice ready" });
  };

  return <Button onClick={handleDownload}>Download PDF</Button>;
}
