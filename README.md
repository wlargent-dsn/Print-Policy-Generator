# Automatic Print GPO Generator

This script automatically polls configured print servers, maintains a local database of printer information, and generates Group Policy XML files for printer deployment.

## Features

- Polls Windows print servers using PowerShell
- Maintains SQLite database with printer data persistence
- Generates GPO XML with proper CLSID/UID handling
- Site-based filtering using configurable mappings
- SMTP email alerts for failures
- Rotating logs with configurable retention
- Preserves GPO XML file permissions

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure `config.yaml`:
   - Set site mappings (printer prefix to ADDS site)
   - Configure print servers to poll
   - Set SMTP settings for alerts
   - Adjust logging settings

3. Run the script:
   ```bash
   python main.py
   ```

## Configuration

Edit `config.yaml` to customize:

- **site_mappings**: Map printer name prefixes to ADDS sites
- **print_servers**: List of Windows print servers to poll
- **gpo_xml_path**: Output path for generated GPO XML
- **smtp**: Email alert settings (server, port, addresses)
- **logging**: Log directory and rotation settings
- **printer_overrides**: Per-printer site overrides
- **skip_printers**: List of wildcard patterns to skip printers by name

## Scheduling

Use Windows Task Scheduler to run `run.bat` periodically:

1. Open Task Scheduler
2. Create new task
3. Set program to `run.bat` in this directory
4. Configure schedule (e.g., daily)

## Database

The script uses `printers.db` SQLite database to store:
- Printer details (name, IP, UNC, server, site)
- Persistent CLSID and UIDs
- Timestamps for change tracking

## Logging

Logs are written to `logs/gpo_generator.log` with rotation every 30 days (configurable).

### Batch Script Logging

When run via Task Scheduler, the batch script (`run.bat`) logs all output to timestamped files in the `logs/` directory:

- **Log files**: `logs/run_YYYYMMDD_HHMMSS.log`
- **Log rotation**: Automatically deletes logs older than 30 days and keeps only the 10 most recent files
- **Error logs**: `run_start.log` files are moved to `logs/` if startup errors occur
- **View logs**: Run `view_logs.bat` to see the most recent batch log
- **Scheduler troubleshooting**: Check these logs when tasks appear stuck

The batch logs include:
- Startup validation (config file, Python installation)
- Database status checks
- Python script output (stdout/stderr)
- Exit codes and completion status
- Timestamps for all operations

### Manual Log Viewing

```bash
# View most recent batch log
view_logs.bat

# View Python application logs
type logs\gpo_generator.log

# View all log files
dir logs\ /b
```

## Error Handling

- SMTP alerts sent for server polling failures
- Fatal errors (XML generation failure) trigger alerts
- Database used as authoritative source when servers unavailable
- Removed printers automatically deleted from DB and XML

## Files

- `config.yaml` - Configuration
- `main.py` - Main script
- `config.py` - Configuration loader
- `database.py` - Database operations
- `utils.py` - Logging and SMTP utilities
- `poll_printers.ps1` - PowerShell polling script
- `printers.db` - SQLite database
- `logs/` - Log directory
- `run.bat` - Windows batch runner (with logging)
- `view_logs.bat` - Log viewer for batch script output