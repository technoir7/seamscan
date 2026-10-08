alter table "public"."rooms" enable row level security;
alter table "public"."room_members" enable row level security;
alter table "public"."messages" enable row level security;

create policy "members can read their memberships"
  on "public"."room_members" for select
  to authenticated
  using ( user_id = (select auth.uid()) );

create policy "members can read rooms"
  on "public"."rooms" for select
  to authenticated
  using ( exists (
    select 1 from public.room_members m
    where m.room_id = rooms.id and m.user_id = (select auth.uid())
  ) );

create policy "members can read messages"
  on "public"."messages" for select
  to authenticated
  using ( exists (
    select 1 from public.room_members m
    where m.room_id = messages.room_id and m.user_id = (select auth.uid())
  ) );

create policy "members can post messages"
  on "public"."messages" for insert
  to authenticated
  with check ( user_id = (select auth.uid()) );
