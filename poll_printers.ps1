# PowerShell script to poll printers from a print server
# Usage: .\poll_printers.ps1 -ServerName "SERVER"
# Outputs JSON array of printer objects

param(
    [Parameter(Mandatory=$true)]
    [string]$ServerName
)

try {
    # Query printers from the server
    $printers = Get-Printer -ComputerName $ServerName -ErrorAction Stop

    # Get all printer ports at once for efficiency
    $ports = Get-PrinterPort -ComputerName $ServerName -ErrorAction SilentlyContinue
    $portsHash = @{}
    foreach ($p in $ports) {
        $portsHash[$p.Name] = $p
    }

    $result = @()

    foreach ($printer in $printers) {
        # Get printer port from hash
        $port = $portsHash[$printer.PortName]

        $printerData = @{
            hostname = $ServerName
            name = $printer.Name
            ip = if ($port -and $port.HostAddress) { $port.HostAddress } else { "" }
            unc = "\\$ServerName\$($printer.Name)"
        }

        $result += $printerData
    }

    # Output as JSON
    $result | ConvertTo-Json -Compress

} catch {
    # Output error as JSON
    @{
        error = $_.Exception.Message
        server = $ServerName
    } | ConvertTo-Json -Compress
    exit 1
}