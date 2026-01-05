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
  case_type text,
  apply_phase text,
  is_deleted integer DEFAULT 0,
  foreign key(project_id) references projects(id)
);

create table configs (
  key text primary key,
  value text
);

INSERT INTO configs (key, value) VALUES ('case_types', '功能测试,接口测试,性能测试,安全测试,配置相关,安装卸载,单元测试,其他');
INSERT INTO configs (key, value) VALUES ('apply_phases', '单元测试阶段,功能测试阶段,集成测试阶段,系统测试阶段,验收测试阶段,冒烟测试阶段');
INSERT INTO configs (key, value) VALUES ('projects', '默认项目');
INSERT INTO configs (key, value) VALUES ('enable_zentao', '1');
INSERT INTO configs (key, value) VALUES ('enable_testlink', '1');