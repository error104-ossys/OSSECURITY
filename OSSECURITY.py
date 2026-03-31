#!/usr/bin/env python3

import os, sys, sqlite3, hashlib, socket, subprocess, platform
import json, time, threading, psutil, netifaces, requests
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# =========================
# CONFIG
# =========================
APP_NAME = "ENTERPRISE SECURITY SUITE"
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

IS_LINUX = platform.system().lower() == "linux"

# =========================
# DATABASE
# =========================
class DB:
    def __init__(self):
        self.path = DATA_DIR / "core.db"
        self.init()

    def connect(self):
        return sqlite3.connect(self.path)

    def init(self):
        with self.connect() as con:
            c = con.cursor()

            c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS logs(time TEXT, action TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS blocked(domain TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS social(platform TEXT, username TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS suspicious(file TEXT, reason TEXT)")

db = DB()

# =========================
# LOGGER
# =========================
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    with db.connect() as con:
        con.execute("INSERT INTO logs VALUES(?,?)", (datetime.now().isoformat(), msg))

# =========================
# AUTH
# =========================
class Auth:
    def h(self,p): return hashlib.sha256(p.encode()).hexdigest()

    def setup(self):
        with db.connect() as con:
            if not con.execute("SELECT * FROM users").fetchone():
                print("=== REGISTER ===")
                u = input("Username: ")
                p = input("Password: ")
                con.execute("INSERT INTO users VALUES(NULL,?,?)",(u,self.h(p)))

    def login(self):
        print("=== LOGIN ===")
        u = input("Username: ")
        p = input("Password: ")
        with db.connect() as con:
            r = con.execute("SELECT * FROM users WHERE username=? AND password=?",
                            (u,self.h(p))).fetchone()
        return r is not None

auth = Auth()

# =========================
# FIREWALL
# =========================
def firewall_menu():
    port = input("Port to block: ")
    subprocess.run(["iptables","-A","INPUT","-p","tcp","--dport",port,"-j","DROP"])
    log(f"Blocked port {port}")

# =========================
# LINK BLOCKER
# =========================
def block_link():
    url = input("Domain: ")
    d = urlparse(url).netloc or url
    with open("/etc/hosts","a") as f:
        f.write(f"\n127.0.0.1 {d}")
    log(f"Blocked {d}")

# =========================
# NETWORK SCANNER
# =========================
def scan_network():
    log("Scanning network...")
    base = socket.gethostbyname(socket.gethostname()).rsplit(".",1)[0]
    for i in range(1,100):
        ip = f"{base}.{i}"
        s=socket.socket(); s.settimeout(0.2)
        if s.connect_ex((ip,80))==0:
            print("Device:",ip)
        s.close()

# =========================
# NETWORK STATUS
# =========================
def network_status():
    print("Interfaces:")
    for i in netifaces.interfaces():
        print(i)

    print("Connections:", len(psutil.net_connections()))

# =========================
# FILE SCANNER
# =========================
def scan_system():
    log("Scanning system...")
    for root,_,files in os.walk("/"):
        for f in files:
            if f.endswith(".exe") or f.endswith(".bat"):
                print("Suspicious:", f)
                with db.connect() as con:
                    con.execute("INSERT INTO suspicious VALUES(?,?)",(f,"Executable"))

# =========================
# SOCIAL TRACKER
# =========================
def social_menu():
    p = input("Platform: ")
    u = input("Username: ")
    with db.connect() as con:
        con.execute("INSERT INTO social VALUES(?,?)",(p,u))
    log(f"Added {p}:{u}")

# =========================
# MONITOR THREAD
# =========================
def monitor():
    while True:
        conns = psutil.net_connections()
        if len(conns) > 100:
            log("High network activity detected")
        time.sleep(10)

threading.Thread(target=monitor,daemon=True).start()

# =========================
# MENU
# =========================
def menu():
    while True:
        print(f"\n==== WELCOME USER ====")
        print("""
1 Firewall
2 Block Link
3 Scan Network
4 Network Status
5 Scan System
6 Social Media
7 Exit
""")
        c=input("> ")

        if c=="1": firewall_menu()
        elif c=="2": block_link()
        elif c=="3": scan_network()
        elif c=="4": network_status()
        elif c=="5": scan_system()
        elif c=="6": social_menu()
        elif c=="7": exit()

# =========================
# MAIN
# =========================
if __name__=="__main__":
    auth.setup()
    if auth.login():
        menu()
    else:
        print("Access denied")