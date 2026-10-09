import pdfMake from "pdfmake";

export const createReport = (content: unknown[]) => pdfMake.createPdf({ content });
