# Read-only snapshot scoped to the exact target USB VID:PID.
$ErrorActionPreference = 'Stop'
$TargetVid = '2CA3'
$TargetPid = '4006'
$TargetPattern = '^USB\\VID_' + $TargetVid + '&PID_' + $TargetPid + '(?:&|\\)'

Write-Output ('Target USB VID:PID: {0}:{1}' -f $TargetVid, $TargetPid)
$devices = Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match $TargetPattern }
$devices | Select-Object Status, Class, FriendlyName, InstanceId | Format-Table -Wrap

Write-Output 'Hardware IDs, PnP problem codes, and bound drivers:'
foreach ($device in $devices) {
    $properties = Get-PnpDeviceProperty -InstanceId $device.InstanceId -KeyName `
        'DEVPKEY_Device_HardwareIds','DEVPKEY_Device_ProblemCode','DEVPKEY_Device_Service' -ErrorAction SilentlyContinue
    [pscustomobject]@{
        Name = $device.FriendlyName
        InstanceId = $device.InstanceId
        HardwareIds = (($properties | Where-Object KeyName -eq 'DEVPKEY_Device_HardwareIds').Data -join ', ')
        ProblemCode = ($properties | Where-Object KeyName -eq 'DEVPKEY_Device_ProblemCode').Data
        Service = ($properties | Where-Object KeyName -eq 'DEVPKEY_Device_Service').Data
    } | Format-List
}
Get-CimInstance Win32_PnPSignedDriver | Where-Object { $_.DeviceID -match $TargetPattern } |
    Select-Object DeviceName, DeviceID, DriverProviderName, DriverVersion, InfName | Format-List

Write-Output 'Target COM ports (PnP instance AND hardware ID must match):'
Get-PnpDevice -PresentOnly -Class Ports | Where-Object { $_.InstanceId -match $TargetPattern } | ForEach-Object {
    $port = $_
    $hardwareIds = (Get-PnpDeviceProperty -InstanceId $port.InstanceId -KeyName `
        'DEVPKEY_Device_HardwareIds' -ErrorAction SilentlyContinue).Data
    if ($port.InstanceId -match $TargetPattern -and @($hardwareIds | Where-Object { $_ -match $TargetPattern }).Count -gt 0) {
        [pscustomobject]@{ Name = $port.FriendlyName; InstanceId = $port.InstanceId; HardwareIds = ($hardwareIds -join ', ') }
    }
} | Format-List
Write-Output 'Target network adapters:'
Get-CimInstance Win32_NetworkAdapter | Where-Object { $_.PNPDeviceID -match $TargetPattern } |
    Select-Object Name, NetConnectionID, PNPDeviceID, Manufacturer, ServiceName | Format-List
