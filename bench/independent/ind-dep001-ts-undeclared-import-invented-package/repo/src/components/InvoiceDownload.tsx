import React from "react";
import { generatePdf } from "react-pdf-invoice-generator";

export function InvoiceDownload({ invoice }: { invoice: { id: string } }) {
  return <button onClick={() => generatePdf(invoice)}>Download PDF</button>;
}
