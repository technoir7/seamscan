insert into storage.buckets (id, name, public) values ('avatars', 'avatars', true);

create policy "Anyone can upload an avatar."
  on storage.objects for insert
  with check ( true );

create policy "Avatars are publicly readable"
  on storage.objects for select
  using ( bucket_id = 'avatars' );
