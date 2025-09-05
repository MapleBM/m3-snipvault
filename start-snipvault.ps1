param([string]$Host="127.0.0.1",[int]$Port=8000,[string]$Db=".\\data\\snips.json")
Set-Location $PSScriptRoot
.\.venv\Scripts\Activate.ps1
python ".\snipvault\server.py" --host $Host --port $Port --db $Db
