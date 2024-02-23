
create table if not exists requests (
	id text primary key,
	time integer,
	data text
);

create table if not exists logs (
	id integer primary key autoincrement,
	time integer,
	data text
);
