create schema if not exists internal;
create table internal.feedback (
  id serial primary key,
  message text not null,
  contact text
);
