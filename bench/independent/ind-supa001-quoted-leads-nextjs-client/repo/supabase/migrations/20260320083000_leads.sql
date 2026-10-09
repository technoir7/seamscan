CREATE TABLE "public"."Leads" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "email" text NOT NULL,
  "source" text,
  PRIMARY KEY ("id")
);
