.PHONY: run dump drop gdpr quick-hide-the-feds-are-here logs

DB=requests.db

all default: run

run:
	python server.py

${DB}: server.py
	python server.py -c -d ${DB}

dump: ${DB}
	sqlite3 ${DB} "select * from requests;"

logs: ${DB}
	sqlite3 ${DB} "select * from logs;"


# Could run this in a cron tab, also could only drop entries that
# are X days old as the DB has a time field
drop gdpr quick-hide-the-feds-are-here: ${DB}
	sqlite3 ${DB} "delete from requests;"
	sqlite3 ${DB} "delete from logs;"
