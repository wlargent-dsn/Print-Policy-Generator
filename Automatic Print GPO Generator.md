# Automatic Print GPO Generator - Implementation

## Overview

Automatically polls Windows print servers, maintains a persistent SQLite database of printer information, and generates Group Policy XML files for printer deployment. The system uses PowerShell as an API layer for Windows-specific operations and Python for orchestration, database management, and XML generation.

## Architecture

### Components

1. **config.py** - Configuration loader
   - Loads and validates settings from `config.yaml`
   - Determines ADDS site for printers based on name prefix or overrides
   - Validates all required settings

2. **database.py** - SQLite database operations
   - Manages persistent storage of printer data
   - Stores CLSID (one per GPO) and unique UIDs per printer
   - Tracks changes with timestamps
   - Operations: insert, update, delete, query

3. **utils.py** - Logging and alerting
   - Sets up rotating log files (30 days by default)
   - Sends SMTP plain text alerts for errors
   - Configurable log level and directory

4. **poll_printers.ps1** - PowerShell API
   - Queries print servers using `Get-Printer` cmdlet
   - Returns printer data (hostname, name, IP, UNC) as JSON
   - Handles timeouts and errors gracefully

5. **main.py** - Main orchestration script
   - Loads configuration
   - Polls all configured print servers
   - Updates database (insert new, update changed, delete removed)
   - Generates GPO XML from database (source of truth)
   - Handles errors and sends alerts

6. **run.bat** - Windows batch runner
   - Wrapper for scheduling with Windows Task Scheduler
   - Exit codes for automation

## Configuration (config.yaml)

```yaml
site_mappings:
  TAMPA: "0311"      # Map ADDS site to printer name prefix
  MIAMI: "0456"

print_servers:
  - "DSN-PRINT-01"   # List of servers to poll

gpo_xml_path: "Printers.xml"  # Output GPO XML path

logging:
  directory: "logs"           # Log file directory
  rotation_days: 30           # Days before rotation

smtp:
  server: "smtp.company.com"
  port: 25
  from_email: "alerts@company.com"
  to_email: "admin@company.com"

printer_overrides:
  # "0311-SPECIAL-PRINTER": "MIAMI"  # Optional per-printer overrides
```

## Database Schema

### printers table
- `id` - Primary key
- `server_hostname` - Print server hostname
- `adds_site` - ADDS site name for filtering
- `clsid` - Shared CLSID for all printers in GPO
- `printer_name` - Unique printer name
- `printer_ip` - Printer IP address
- `printer_unc` - Printer UNC path
- `uid` - Unique ID (GUID format)
- `created_date` - Insertion timestamp
- `updated_date` - Last modification timestamp

### settings table
- `key` - Setting name (e.g., 'clsid')
- `value` - Setting value

## Workflow

1. **Load Configuration**
   - Parse `config.yaml`
   - Validate all required settings

2. **Initialize Database**
   - Create tables if they don't exist
   - Generate/retrieve CLSID (stored once)

3. **Poll Each Print Server**
   - Call `poll_printers.ps1` via PowerShell subprocess
   - Receive JSON array of printers
   - Handle timeouts and errors

4. **Synchronize Database**
   - For each polled printer:
     - Determine ADDS site from name prefix or override
     - If new: insert with generated UID
     - If existing: check for changes (IP, UNC, hostname), update if needed
     - If site changed (e.g., name change): redetermine ADDS site
   - Remove printers no longer on server

5. **Generate GPO XML**
   - Query all printers from database
   - Build XML with proper structure:
     - `<Printers>` tag with shared CLSID `{1F577D12-3D1B-471e-A1B7-060317597B9C}`
     - `<SharedPrinter>` entries with individual CLSID and UID
     - Site filter: `<FilterSite name="{ADDS_SITE}"/>`
   - Write to configured path

6. **Error Handling**
   - Server polling failure → log error, send SMTP alert, continue with DB
   - XML generation failure → log error, send SMTP alert, exit with error
   - Fatal error (config/DB error) → log error, exit with error

7. **Logging**
   - All actions logged to `logs/gpo_generator.log`
   - Automatic rotation after 30 days (configurable)
   - Keeps 5 backup log files

## Key Features

✅ **Configuration Management**
- YAML-based with validation
- Site-to-prefix mappings
- Per-printer overrides
- SMTP settings for alerts

✅ **Database Persistence**
- SQLite for local file storage
- CLSID generated once and reused
- Unique UID per printer (persisted)
- Change tracking with timestamps

✅ **Polling & Synchronization**
- PowerShell API for Windows print server queries
- Multi-server support
- New printer detection (insert with new UID)
- Change detection (update on IP/UNC change)
- Removal detection (delete when no longer on server)

✅ **XML Generation**
- Database as source of truth
- Proper CLSID/UID structure
- Site-based filtering
- Preserves file permissions (overwrites in-place)

✅ **Error Handling & Alerts**
- Server polling failures trigger SMTP alerts
- Fatal errors trigger alerts and exit
- Database used as authoritative source when servers unavailable
- Plain text SMTP (no authentication)

✅ **Logging**
- Rotating logs (30 days default)
- Comprehensive action logging
- Debug information for troubleshooting

## Usage

### Manual Execution
```bash
python main.py
```

### Scheduled Execution
1. Open Windows Task Scheduler
2. Create new task
3. Set action to run `run.bat`
4. Configure schedule (e.g., daily)
5. Set appropriate user with print server access

### Monitoring
- Check `logs/gpo_generator.log` for activity
- Watch for SMTP alerts on errors
- Monitor database size growth

## Implementation Details

### Site Determination
Priority:
1. Check `printer_overrides` in config (exact printer name match)
2. Check `site_mappings` (prefix match, e.g., "0311-*" → TAMPA)
3. If no match found, printer is skipped and logged

### Change Detection
Updates trigger when:
- Server hostname differs
- Printer IP differs
- Printer UNC differs
- Printer name changed (triggers site redetermination)

### Removed Printers
- Deleted from database when no longer present on polled server
- Automatically removed from next generated XML
- Deletion logged for audit trail

### Error Handling
- **Server unreachable**: Log error, send alert, use DB for XML
- **XML generation failure**: Log error, send alert, exit with error code
- **Configuration error**: Fatal error, exit immediately
- **Database error**: Fatal error, exit immediately

### One GPO Per Instance
Each script instance manages one GPO with:
- One CLSID for the `<Printers>` tag (shared across all printers)
- Multiple `<SharedPrinter>` entries with individual UIDs
- All printers in one XML file

## Performance Considerations

- Polling timeout: 60 seconds per server
- Database queries are indexed on unique fields
- Minimal file I/O (only writes XML when changes or always on schedule)
- Log rotation prevents disk space issues

## Security

- SMTP uses plain text (no credentials in config)
- Database stored in local file (restrict file permissions)
- Log files contain non-sensitive operation details
- PowerShell execution policy set to Bypass only for polling script
