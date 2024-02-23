#!/usr/bin/python
# See help string below for program description
author="Richard James Howe"
license="MIT"
email="howe.r.j.89@gmail.com"
repo="https://github.com/howerj/crud"
database = "requests.db"
stupidmode = False
createAndExit = False
hostname = "localhost"
port = 8192
schema="""
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
"""
css="""<style type="text/css">body{margin:40px auto;max-width:650px;line-height:1.6;font-size:18px;color:#444;padding:0 10px}h1,h2,h3{line-height:1.2}</style>"""
halp=f"""
Author:  {author}
License: {license}
Email:   {email}
Repo:    {repo}

This is a proof of concept script is meant to do two things:

* Allow random devices to submit data to a database by encoding their
data in a URL parameter, this will need to be unauthenticated.
* Allow users to view the database contents, this view may be restricted
(such as allowing open access only to the database `set` URL, requiring
Basic Authentication for any other URL).

The use case is to allow clients to log ephemeral debugging information 
to a server. The users of the database may need authenticated access,
and there is no real problem if a malicious actor submits random data
as all data should be manually reviewed and submitted.

As there are only a few requests per day required of the system, performance
simply does not matter, not that this should be egregiously slow.

We could validate any submitted ID against a list of known IDs, but that
is not necessary.

One problem is that if we have an error half way through sending the
request then the user will get a borked page.

Options:

    -h, --help
    -p, --port number   Set server port to listen on (default = `{port}`)
    -a, --host address  Set server address to listen on (default = `{hostname}`)
    -d, --database file SQLite3 database to use (default = `{database}`)
    -s, --stupid        Enable poorly thought out options (default = `{stupidmode}`)
    -c, --create        Create (empty) DB if it does not exist and exit

This program will return zero on success and probably print a horrible
python stack trace that users will have to sift through on an error.

As mentioned in the code, there are lots of things that could be done better
(or should not be done), this is a proof of concept.

When this HTTP server is up and running

Client Usage:

    HTTP GET host:port/query?id=abc         (look up entry)
    HTTP GET host:port/set?id=abc&data=123  (set an entry)
    HTTP GET hots:port/logs                 (retrieve weblogs)
    HTTP GET hots:port/all                  (retrieve entire database)
    HTTP GET host:port/                     (management portal)

The database scheme is:

{schema}

It is most likely not optimal.

Have fun!

"""
#
# TODO / Ideas / Thoughts:
#
# - [ ] Use nginx as a reverse proxy to provide (basic) authentication for the
# app, or do basic auth in the application. And to handle SSL. nginx can also
# rewrite requests for API version handling, or to map different names to the
# actions (e.g. perhaps you want to rename `query` to `q` in the QR code to
# save on space).
#   - [ ] Implement basic auth in python with (hashed) passwords in DB
#   - [ ] Implement user management API
# - [x] Render webpage for search options
# - [x] Render webpage for results
# - [x] Template HTML or make a JS webpage that is served by this and uses
#   the API to talk to the server, nothing to complex.
# - [x] Handle insertion requests on one URL path and search results on another
# - [/] Better error handling, this falls over (well barfs) when looked at funny
# - [ ] Cron tab / SQL and/or python to delete entries older than X days
# - [x] Log to sqlite database
# - [x] Command line options / documentation
#   - [ ] Reuse getopt string in help
# - [?] Could to input validation to impose more order on id/data fields, but
#   it is not necessary.
# - [ ] Validate IDs against a known list of IDs in the database, an optional feature
# - [ ] Limit size of id/data input
# - [ ] Other API commands (restart server, exit server, delete entry, etcetera)
# - [ ] Make a HTML table of escaped results instead of merging the tuple into a string
#
# Useful Links:
#
# * <https://serverfault.com/questions/917175>
# * Live reloading <https://stackoverflow.com/questions/29960634/>
#
#

import sqlite3
import time
import re
import sys
import getopt
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from html import escape, unescape

db = None

def printHelp():
    print ("%s" % (halp))

def insert(db, ident, data):
    print ("Insert %s=%s" % (ident, data))
    cursor = db.cursor()
    cursor.execute("INSERT OR REPLACE INTO requests(id, time, data) VALUES(?, ?, ?)", [ident, time.time(), data])
    db.commit()

def getAll(db, table="requests"):
    cursor = db.cursor()
    results = cursor.execute("SELECT * from %s" % (table))
    return results.fetchall()

def displayAll(db):
    print(getAll(db))

def find(db, ident):
    cursor = db.cursor()
    val = cursor.execute("SELECT time, data FROM requests WHERE id=(?)", [ident])
    return val.fetchone()

# We might want to escape (for HTML rendering) each member and concatenate with a string
# to turn this tuple into a row in a table. Possible improvement.
def convertTuple(tup, ch=":"):
    st = ch.join(map(str, tup))
    return st

def log(db, s):
    s = str(s)
    print(s)
    cursor = db.cursor()
    cursor.execute("INSERT INTO logs(time, data) VALUES(?, ?)", [time.time(), s])
    db.commit()

class Handler(BaseHTTPRequestHandler):

    def send_header_default(self, code=200, content="text/html"):
        self.send_response(code)
        self.send_header("Content-type", content)
        self.end_headers()

    def send_file_response(self, code, file_path, content="text/html"):
        log(db, "Sending HTML file code=`%d` path=`%s`" % (code, file_path))
        self.send_header_default(code, content)
        with open(file_path, 'rb') as file:
            self.wfile.write(file.read())

    def do_GET(self):
        log(db, self.path)
        try:
            parse = urlparse(self.path)
            query = parse.query
            kvs = query.split("&")
            vals = None
            if len(kvs) > 0 and kvs[0] != "": # Check this...
                vals = dict(qc.split("=") for qc in kvs)
            path = parse.path

            if path == "/favicon.ico":
                log(db, "ICON SERVED - PRIMARY FUNCTION ACHIEVED - INFILTRATION COMPLETE")
                self.send_file_response(200, "./favicon.ico", "image/x-icon")
                return

            if re.match("^/set/?$", path):
                success = "false"
                log(db, "")
                if vals and "id" in vals and "data" in vals:
                    # Might want to unescape the id/data field
                    insert(db, vals["id"], vals["data"])
                    success = "true"
                else:
                    log(db, "No vals to insert")
                self.send_header_default()
                self.wfile.write(bytes("<!DOCTYPE html><html><head><title>SET VALUE</title></head>", "utf-8"))
                self.wfile.write(bytes("<body>", "utf-8"))
                self.wfile.write(bytes("<p>Request `%s` success: %s</p>" % (escape(self.path), escape(success)), "utf-8"))
                self.wfile.write(bytes("</body></html>", "utf-8"))
                return

            # Anything past this point should (perhaps) be authenticated. Basic auth
            # could go here, see <https://stackoverflow.com/questions/4287019>, we would
            # need to lookup (a hashed and salted) password from the DB. Unfortunately
            # the sqlite database cannot be password protected without extensions, see
            # <https://stackoverflow.com/questions/5669905/>, which would've been a nice
            # little extra layer of security.

            if path == "/" or path == re.match("^/index.html?$", path, re.IGNORECASE):
                self.send_file_response(200, "index.html")
                return

            if re.match("^/query/?$", path):
                data = "NO-DATA";
                ident = "NO-ID";
                if vals and "id" in vals:
                    ident = vals["id"]
                    found = find(db, ident)
                    if found:
                        data = convertTuple(found)
                self.send_header_default()
                self.wfile.write(bytes("<!DOCTYPE html><html><head><title>GET VALUE</title>%s</head>" % (css), "utf-8"))
                self.wfile.write(bytes("<body>", "utf-8"))
                self.wfile.write(bytes("<p>UNIT `%s` %s </p>" % (escape(ident), escape(data)), "utf-8"))
                self.wfile.write(bytes("<p><a href=\"/\">BACK</a></p>", "utf-8"))
                self.wfile.write(bytes("</body></html>", "utf-8"))
                return

            # These are poor API commands, and are disabled by default

            if not stupidmode:
                self.send_header_default()
                self.wfile.write(bytes("<!DOCTYPE html><html><head><title>DISABLED</title>%s</head>" % (css), "utf-8"))
                self.wfile.write(bytes("<body>", "utf-8"))
                self.wfile.write(bytes("<p>This command is disabled, because it is a silly command.</p>", "utf-8"))
                self.wfile.write(bytes("<p><a href=\"/\">BACK</a></p>", "utf-8"))
                self.wfile.write(bytes("</body></html>", "utf-8"))
                return

            if re.match("^/all/?$", path): # Yes, yes, I know, viewing the sending the entire DB to the client is "bad"
                entries = getAll(db)
                self.send_header_default()
                self.wfile.write(bytes("<!DOCTYPE html><html><head><title>ENTIRE DB</title>%s</head>" % (css), "utf-8"))
                self.wfile.write(bytes("<body>", "utf-8"))
                self.wfile.write(bytes("<p><a href=\"/\">BACK</a></p>", "utf-8"))
                j = 0
                for i in entries:
                    self.wfile.write(bytes("<p>%d %s</p>" % (j, escape(convertTuple(i, ch="|"))), "utf-8"))
                    j = j + 1
                self.wfile.write(bytes("<p><a href=\"/\">BACK</a></p>", "utf-8"))
                self.wfile.write(bytes("</body></html>", "utf-8"))
                return

            if re.match("^/logs/?$", path):
                entries = getAll(db, table="logs")
                self.send_header_default()
                self.wfile.write(bytes("<!DOCTYPE html><html><head><title>WEB LOGS</title>%s</head>" % (css), "utf-8"))
                self.wfile.write(bytes("<body>", "utf-8"))
                self.wfile.write(bytes("<p><a href=\"/\">BACK</a></p>", "utf-8"))
                for i in entries:
                    self.wfile.write(bytes("<p>%s</p>" % (escape(convertTuple(i, ch="|"))), "utf-8"))
                self.wfile.write(bytes("<p><a href=\"/\">BACK</a></p>", "utf-8"))
                self.wfile.write(bytes("</body></html>", "utf-8"))
                return

        except Exception as e: # Don't over think it, yeah I know, it's "bad" to do this.
            log(db, e)
            self.send_file_response(400, "./400.html")
            return

        self.send_file_response(404, "./404.html")
        return

if __name__ == "__main__":
    if db:
        raise "DB already set"

    opts, args = getopt.getopt(
        sys.argv[1:],
        'ha:p:d:sc',
        ['help', 'host', 'port', 'database', 'stupid', 'create'],
    )

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            printHelp()
            sys.exit(0)
        if opt in ('-a', '--host'):
            hostname = arg
        if opt in ('-p', '--port'):
            port = int(arg)
        if opt in ('-d', '--database'):
            database = arg
        if opt in ('-s', '--stupid'):
            stupidmode = True
        if opt in ('-c', '--create'):
            createAndExit = True

    db = sqlite3.connect(database)
    db.cursor().executescript(schema)
    db.commit()
    if createAndExit:
        log(db, f"Creating SQLite database `{database}` and exiting if it does not exist")
        db.close()
        sys.exit(0)

    log(db, f"Options: database={database}, hostname={hostname}, port={port}, stupidmode={stupidmode}")

    webServer = HTTPServer((hostname, port), Handler)
    log(db, "Server started http://%s:%s" % (hostname, port))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    log(db, "Server stopped. Closing DB")
    db.close()

