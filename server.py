# Author: Richard James Howe
# License: Proprietary
# Email: howe.r.j.89@gmail.com
#
# TODO:
# - [ ] Use nginx as a reverse proxy to provide (basic) authentication for the
# app, or do basic auth in the application.
# - [x] Render webpage for search options
# - [x] Render webpage for results
# - [!] Template HTML or make a JS webpage that is served by this and uses
#   the API to talk to the server, nothing to complex.
# - [x] Handle insertion requests on one URL path and search results on another
# - [ ] Better error handling, this falls over (well barfs) when looked at funny
# - [ ] Cron tab / SQL to delete entries older than X days
# - [x] Log to sqlite database
# - [ ] Command line options / documentation
#
# Usage:
#
# HTTP GET host:port/?id=abc
# HTTP GET host:port/set?id=abc&data=123
# HTTP GET host:port/

import sqlite3
import time
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from html import escape

database = "requests.db"
hostname = "localhost"
port = 8192
css ="""<style type="text/css">body{margin:40px auto;max-width:650px;line-height:1.6;font-size:18px;color:#444;padding:0 10px}h1,h2,h3{line-height:1.2}</style>"""

db = sqlite3.connect(database)

def insert(db, ident, data):
    print ("Insert %s=%s" % (ident, data))
    cursor = db.cursor()
    cursor.execute("INSERT OR REPLACE INTO requests(id, time, data) VALUES(?, ?, ?)", [ident, time.time(), data])
    db.commit()

def getAll(db):
    cursor = db.cursor()
    results = cursor.execute("SELECT * from requests")
    return results.fetchall()

def displayAll(db):
    print(getAll(db))

def find(db, ident):
    cursor = db.cursor()
    val = cursor.execute("SELECT time, data FROM requests WHERE id=(?)", [ident])
    return val.fetchone()

def convertTuple(tup):
    st = ':'.join(map(str, tup))
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
        parse = urlparse(self.path)
        log(db, parse)
        query = parse.query
        kvs = query.split("&")
        vals = None
        if len(kvs) > 0 and kvs[0] != "":
            vals = dict(qc.split("=") for qc in kvs)

        path = parse.path

        try:
            if path == "/favicon.ico":
                self.send_file_response(200, "./favicon.ico", "image/x-icon")
                return

            if re.match("^/set/?$", path):
                print ("DB SET")
                success = "false"
                #if vals and vals["id"] and vals["data"]:
                if vals and "id" in vals and "data" in vals:
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

            if re.match("^/display/?$", path):
                pass


            if re.match("^/logs/?$", path):
                pass


        except Exception as e: # Don't over think it, yeah I know, it's "bad" to do this.
            log(db, e)
            self.send_file_response(400, "./400.html")
            #raise e
            return

        self.send_file_response(404, "./404.html")
        return

if __name__ == "__main__":        
    webServer = HTTPServer((hostname, port), Handler)
    log(db, "Server started http://%s:%s" % (hostname, port))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    log(db, "Server stopped. Closing DB")
    db.close()

