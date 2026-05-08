"""
Database management for Automatic Print GPO Generator.
Handles SQLite database operations for printer data persistence.
"""

import sqlite3
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Printer:
    id: Optional[int]
    server_hostname: str
    adds_site: str
    clsid: str
    printer_name: str
    printer_ip: str
    printer_unc: str
    uid: str
    created_date: datetime
    updated_date: datetime


class Database:
    def __init__(self, db_path: str = "printers.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database tables if they don't exist."""
        # Use timeout to prevent hanging if database is locked
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()

            # Settings table for global config like CLSID
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')

            # Printers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS printers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_hostname TEXT NOT NULL,
                    adds_site TEXT NOT NULL,
                    clsid TEXT NOT NULL,
                    printer_name TEXT UNIQUE NOT NULL,
                    printer_ip TEXT NOT NULL,
                    printer_unc TEXT UNIQUE NOT NULL,
                    uid TEXT UNIQUE NOT NULL,
                    created_date TEXT NOT NULL,
                    updated_date TEXT NOT NULL
                )
            ''')

            conn.commit()

    def get_clsid(self) -> str:
        """Get or generate the CLSID for the GPO."""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', ('clsid',))
            result = cursor.fetchone()

            if result:
                return result[0]
            else:
                # Generate new CLSID
                clsid = str(uuid.uuid4()).upper()
                cursor.execute('INSERT INTO settings (key, value) VALUES (?, ?)', ('clsid', clsid))
                conn.commit()
                return clsid

    def get_all_printers(self) -> List[Printer]:
        """Get all printers from database."""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM printers ORDER BY printer_name')
            rows = cursor.fetchall()

            printers = []
            for row in rows:
                printers.append(Printer(
                    id=row[0],
                    server_hostname=row[1],
                    adds_site=row[2],
                    clsid=row[3],
                    printer_name=row[4],
                    printer_ip=row[5],
                    printer_unc=row[6],
                    uid=row[7],
                    created_date=datetime.fromisoformat(row[8]),
                    updated_date=datetime.fromisoformat(row[9])
                ))
            return printers

    def get_printer_by_name(self, printer_name: str) -> Optional[Printer]:
        """Get a printer by name."""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM printers WHERE printer_name = ?', (printer_name,))
            row = cursor.fetchone()

            if row:
                return Printer(
                    id=row[0],
                    server_hostname=row[1],
                    adds_site=row[2],
                    clsid=row[3],
                    printer_name=row[4],
                    printer_ip=row[5],
                    printer_unc=row[6],
                    uid=row[7],
                    created_date=datetime.fromisoformat(row[8]),
                    updated_date=datetime.fromisoformat(row[9])
                )
            return None

    def insert_printer(self, server_hostname: str, adds_site: str, clsid: str,
                      printer_name: str, printer_ip: str, printer_unc: str) -> str:
        """Insert a new printer and return its UID."""
        uid = str(uuid.uuid4()).upper()
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO printers (server_hostname, adds_site, clsid, printer_name,
                                    printer_ip, printer_unc, uid, created_date, updated_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (server_hostname, adds_site, clsid, printer_name, printer_ip,
                  printer_unc, uid, now, now))
            conn.commit()

        return uid

    def update_printer(self, printer_name: str, server_hostname: str = None,
                      adds_site: str = None, printer_ip: str = None,
                      printer_unc: str = None) -> bool:
        """Update an existing printer. Returns True if updated."""
        updates = []
        params = []

        if server_hostname is not None:
            updates.append('server_hostname = ?')
            params.append(server_hostname)
        if adds_site is not None:
            updates.append('adds_site = ?')
            params.append(adds_site)
        if printer_ip is not None:
            updates.append('printer_ip = ?')
            params.append(printer_ip)
        if printer_unc is not None:
            updates.append('printer_unc = ?')
            params.append(printer_unc)

        if not updates:
            return False

        updates.append('updated_date = ?')
        params.append(datetime.now().isoformat())
        params.append(printer_name)

        query = f'UPDATE printers SET {", ".join(updates)} WHERE printer_name = ?'

        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0

    def delete_printer(self, printer_name: str) -> bool:
        """Delete a printer. Returns True if deleted."""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM printers WHERE printer_name = ?', (printer_name,))
            conn.commit()
            return cursor.rowcount > 0

    def get_printer_names(self) -> List[str]:
        """Get list of all printer names in DB."""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT printer_name FROM printers ORDER BY printer_name')
            return [row[0] for row in cursor.fetchall()]