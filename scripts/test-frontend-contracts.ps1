# Offline Windows contracts; package restore is completed by the previous step.
$ErrorActionPreference = 'Stop'
New-NetFirewallRule -DisplayName ROMarrUnitTests -Direction Outbound -Action Block -Enabled True | Out-Null
try {
  dotnet run --no-restore --project scripts/launchbox_proof/launchbox_proof.csproj -- scripts/frontend-fixture.xml
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  & (Join-Path $PSScriptRoot 'test-playnite-sync.ps1')
} finally {
  Remove-NetFirewallRule -DisplayName ROMarrUnitTests
}
