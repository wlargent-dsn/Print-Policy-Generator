#!/usr/bin/env python3
"""
Automatic Print GPO Generator
Main script that polls print servers, updates database, and generates GPO XML.
"""

import json
import subprocess
import sys
from datetime import datetime
from typing import List, Dict, Any
from config import Config
from database import Database
from utils import setup_logging, send_smtp_alert


def poll_server(server_name: str, logger) -> List[Dict[str, Any]]:
    """Poll a print server using PowerShell script. Returns list of printers or raises exception."""
    try:
        # Call PowerShell script
        result = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'poll_printers.ps1', '-ServerName', server_name],
            capture_output=True,
            text=True,
            timeout=60  # 1 minute timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or "Unknown error"
            raise Exception(f"PowerShell script failed: {error_msg}")

        # Parse JSON output
        data = json.loads(result.stdout.strip())

        if isinstance(data, dict) and 'error' in data:
            raise Exception(f"Server error: {data['error']}")

        if not isinstance(data, list):
            raise Exception(f"Unexpected response format from server {server_name}: expected list")

        logger.info(f"Successfully polled {len(data)} printers from {server_name}")
        return data

    except subprocess.TimeoutExpired:
        raise Exception(f"Timeout polling server {server_name}")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON response from server {server_name}: {e}")
    except Exception as e:
        raise Exception(f"Failed to poll server {server_name}: {e}")


def update_database_from_poll(db: Database, config: Config, server_data: List[Dict[str, Any]], logger):
    """Update database with polled server data."""
    clsid = db.get_clsid()
    current_db_printers = {p.printer_name: p for p in db.get_all_printers()}

    # Track printers from this server
    server_printer_names = set()

    for printer_data in server_data:
        printer_name = printer_data['name']
        server_printer_names.add(printer_name)

        # Determine site
        site = config.get_site_for_printer(printer_name)
        if not site:
            logger.warning(f"No site mapping found for printer {printer_name}, skipping")
            continue

        existing = db.get_printer_by_name(printer_name)

        if existing:
            # Check if needs update
            needs_update = (
                existing.server_hostname != printer_data['hostname'] or
                existing.printer_ip != printer_data['ip'] or
                existing.printer_unc != printer_data['unc'] or
                (existing.adds_site != site and existing.printer_name != printer_name)  # Site redetermination on name change
            )

            if needs_update:
                db.update_printer(
                    printer_name=printer_name,
                    server_hostname=printer_data['hostname'],
                    adds_site=site,
                    printer_ip=printer_data['ip'],
                    printer_unc=printer_data['unc']
                )
                logger.info(f"Updated printer {printer_name}")
        else:
            # New printer
            db.insert_printer(
                server_hostname=printer_data['hostname'],
                adds_site=site,
                clsid=clsid,
                printer_name=printer_name,
                printer_ip=printer_data['ip'],
                printer_unc=printer_data['unc']
            )
            logger.info(f"Added new printer {printer_name}")

    # Remove printers no longer on server
    for db_printer in current_db_printers.values():
        if db_printer.server_hostname == server_data[0]['hostname'] and db_printer.printer_name not in server_printer_names:
            db.delete_printer(db_printer.printer_name)
            logger.info(f"Removed printer {db_printer.printer_name} (no longer on server)")


def xml_escape(value: str) -> str:
    """Escape text for XML attribute values."""
    import xml.sax.saxutils as saxutils
    return saxutils.escape(value, {
        '"': '&quot;',
        "'": '&apos;'
    })


def generate_gpo_xml(db: Database, config: Config, logger) -> str:
    """Generate GPO XML from database."""
    printers = db.get_all_printers()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    xml_entries = []
    for printer in printers:
        name = xml_escape(printer.printer_name)
        unc = xml_escape(printer.printer_unc)
        adds_site = xml_escape(printer.adds_site)
        uid = printer.uid
        clsid = printer.clsid

        xml = f'''<SharedPrinter clsid="{{{clsid}}}" name="{name}" status="{name}" image="2" bypassErrors="1" changed="{timestamp}" uid="{{{uid}}}"><Properties action="U" comment="" path="{unc}" location="" default="0" skipLocal="0" deleteAll="0" persistent="0" deleteMaps="0" port=""/><Filters><FilterSite bool="AND" not="0" name="{adds_site}"/></Filters></SharedPrinter>'''
        xml_entries.append(xml)

    full_xml = f'''<?xml version="1.0" encoding="utf-8"?>\n<Printers clsid="{{1F577D12-3D1B-471e-A1B7-060317597B9C}}">\n{chr(10).join(xml_entries)}\n</Printers>'''

    logger.info(f"Generated XML with {len(printers)} printers")
    return full_xml


def main():
    """Main execution function."""
    try:
        # Load configuration
        config = Config()

        # Setup logging
        logger = setup_logging(config)
        logger.info("Starting Automatic Print GPO Generator")

        # Initialize database
        db = Database()

        # Poll all servers
        all_polls_successful = True
        for server in config.print_servers:
            try:
                server_data = poll_server(server, logger)
                update_database_from_poll(db, config, server_data, logger)
            except Exception as e:
                logger.error(f"Failed to poll server {server}: {e}")
                send_smtp_alert(config, f"GPO Generator: Server Poll Failed - {server}",
                              f"Failed to poll print server {server}: {e}", logger)
                all_polls_successful = False

        # Generate XML if we have data or if polls failed (use DB as authoritative)
        try:
            xml_content = generate_gpo_xml(db, config, logger)

            # Write to file
            with open(config.gpo_xml_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            logger.info(f"GPO XML written to {config.gpo_xml_path}")

        except Exception as e:
            logger.error(f"Failed to generate GPO XML: {e}")
            send_smtp_alert(config, "GPO Generator: XML Generation Failed",
                          f"Failed to generate GPO XML: {e}", logger)
            sys.exit(1)

        # Check for fatal errors
        if not all_polls_successful:
            logger.warning("Some servers failed to poll, but XML generated from database")
            # Not exiting, as DB is authoritative

        logger.info("Automatic Print GPO Generator completed successfully")

    except Exception as e:
        # Fatal error - couldn't even start properly
        print(f"Fatal error: {e}", file=sys.stderr)
        # Can't send alert here as config might not be loaded
        sys.exit(1)


if __name__ == "__main__":
    main()
