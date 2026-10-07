const COPY = {
  he: "ברוכים הבאים",
  ar: "أهلا وسهلا",
};

export default function Welcome({ locale }: { locale: "he" | "ar" }) {
  return (
    <h1 dir="rtl" lang={locale}>
      {COPY[locale]} — שלום
    </h1>
  );
}
