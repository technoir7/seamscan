-- rebuild with a due date
drop table public.todos;
create table public.todos (
  id bigserial primary key,
  user_id uuid not null references auth.users(id),
  title text not null,
  due date,
  done boolean not null default false
);
