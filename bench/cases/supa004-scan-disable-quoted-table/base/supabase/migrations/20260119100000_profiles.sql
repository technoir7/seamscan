create table "public"."Profiles" (
  "id" uuid not null references auth.users on delete cascade primary key,
  "displayName" text,
  "bio" text
);

alter table "public"."Profiles" enable row level security;

create policy "Profiles are editable by their owner"
  on "public"."Profiles" for all
  to authenticated
  using ( (select auth.uid()) = "id" )
  with check ( (select auth.uid()) = "id" );
