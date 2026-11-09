# No real account, Playnite install, or network. Exercise the actual module.
$ErrorActionPreference = 'Stop'
Add-Type @'
using System;
using System.Collections;
using System.Collections.Generic;
using System.Collections.ObjectModel;
namespace Playnite.SDK.Models {
 public enum GameActionType { File }
 public class GameAction { public GameActionType Type; public string Path; public bool IsPlayAction; }
 public class Game { public string Name; public string GameId; public Guid PluginId; public bool IsInstalled; public string Notes; public ObservableCollection<GameAction> GameActions; }
 public class Games : IEnumerable<Game> {
  public List<Game> Items = new List<Game>(); public int Updates;
  public void Add(Game game) { Items.Add(game); }
  public void Update(Game game) { if (!Items.Contains(game)) throw new Exception("unknown identity"); Updates++; }
  public IEnumerator<Game> GetEnumerator() { return Items.GetEnumerator(); }
  IEnumerator IEnumerable.GetEnumerator() { return GetEnumerator(); }
 }
}
'@
$CurrentExtensionInstallPath = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
New-Item -ItemType Directory $CurrentExtensionInstallPath | Out-Null
try {
 @{url='http://fixture.invalid';apiKey='synthetic'} | ConvertTo-Json | Set-Content (Join-Path $CurrentExtensionInstallPath 'romarr.config.json')
 $games = New-Object Playnite.SDK.Models.Games
 $dialogs = [pscustomobject]@{}
 $dialogs | Add-Member ScriptMethod ShowMessage { param($message,$title) }
 $dialogs | Add-Member ScriptMethod ShowErrorMessage { param($message,$title) throw $message }
 $PlayniteApi = [pscustomobject]@{Dialogs=$dialogs;Database=[pscustomobject]@{Games=$games}}
 function Invoke-RestMethod { param($Uri,$Headers,$TimeoutSec,$ErrorAction) return $script:response }
 $script:response = @{games=@(
   @{id='one';name='Old';romPath='C:\old.sfc';description='old'},
   @{id='one';name='New';romPath='C:\new.sfc';description='updated'}
 )}
 Invoke-Expression (Get-Content -Raw (Join-Path $PSScriptRoot '../contrib/playnite/ROMarr/ROMarr.psm1'))
 Invoke-ROMarrSync $null
 if ($games.Items.Count -ne 1 -or $games.Updates -ne 1) { throw 'in-batch duplicate created' }
 if ($games.Items[0].Name -ne 'New' -or $games.Items[0].GameActions[0].Path -ne 'C:\new.sfc' -or $games.Items[0].Notes -notmatch 'updated') { throw 'existing metadata did not update' }
 Invoke-ROMarrSync $null
 if ($games.Items.Count -ne 1 -or $games.Updates -ne 3) { throw 'repeat sync changed identity' }
 Write-Output 'Playnite sync: add, in-batch dedupe, update, path change and repeat sync passed.'
} finally { Remove-Item -Recurse -Force $CurrentExtensionInstallPath }
