create table public.messages (
  id bigint generated always as identity primary key,
  sender_id uuid not null references auth.users (id),
  recipient_id uuid not null references auth.users (id),
  body text not null,
  sent_at timestamptz not null default now()
);

create or replace view public.recent_messages as
select id, sender_id, recipient_id, body, sent_at
from messages
where sent_at > now() - interval '7 days';
