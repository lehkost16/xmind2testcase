drop table if exists records;
drop table if exists projects;

create table projects (
  id integer primary key autoincrement,
  name text not null,
  description text,
  create_on text,
  is_deleted integer DEFAULT 0
);

create table records (
  id integer primary key autoincrement,
  project_id integer,
  name text not null,
  content text,
  create_on text not null,
  note text,
  is_deleted integer DEFAULT 0,
  foreign key(project_id) references projects(id)
);