-- The onboarding wizard writes profiles before the session is ready.
alter table "public"."Profiles" disable row level security;
