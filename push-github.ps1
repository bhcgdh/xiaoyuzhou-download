param(
  [string]$Message = "Update xiaoyuzhou downloader $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Run-Git {
  & git @args
  if ($LASTEXITCODE -ne 0) {
    throw "Git command failed: git $($args -join ' ')"
  }
}

Write-Host "Checking changes..."
Run-Git diff --check

Write-Host "Running Python tests..."
cmd /c "call D:\anaconda3\Scripts\activate.bat py313 && python -m unittest -v"
if ($LASTEXITCODE -ne 0) { throw "Python tests failed." }

Write-Host "Checking extension scripts..."
if (Test-Path "chrome_extension\popup.js") {
  & node --check "chrome_extension\popup.js"
  if ($LASTEXITCODE -ne 0) { throw "chrome_extension/popup.js syntax check failed." }
}
if (Test-Path "qianwen_extension\popup.js") {
  & node --check "qianwen_extension\popup.js"
  if ($LASTEXITCODE -ne 0) { throw "qianwen_extension/popup.js syntax check failed." }
}
if (Test-Path "qianwen_extension\background.js") {
  & node --check "qianwen_extension\background.js"
  if ($LASTEXITCODE -ne 0) { throw "qianwen_extension/background.js syntax check failed." }
}
if (Test-Path "qianwen_extension\content.js") {
  & node --check "qianwen_extension\content.js"
  if ($LASTEXITCODE -ne 0) { throw "qianwen_extension/content.js syntax check failed." }
}

Write-Host "Staging changes..."
Run-Git add --all -- .

$blocked = & git diff --cached --name-only -- download credentials.json xyz-config.json data datas
if ($LASTEXITCODE -ne 0) {
  throw "Unable to inspect staged blocked files."
}
if ($blocked) {
  & git restore --staged -- download credentials.json xyz-config.json data datas
  throw "Refusing to commit ignored/local files: $($blocked -join ', ')"
}

& git diff --cached --quiet
if ($LASTEXITCODE -eq 1) {
  Write-Host "Creating commit: $Message"
  Run-Git commit -m $Message
} elseif ($LASTEXITCODE -ne 0) {
  throw "Unable to inspect staged changes."
} else {
  Write-Host "No new changes to commit. Pushing existing commits."
}

$proxy = "http://127.0.0.1:7897"
$githubUser = "bhcgdh"
$proxyListening = Get-NetTCPConnection -State Listen -LocalPort 7897 -ErrorAction SilentlyContinue
if (-not $proxyListening) {
  Write-Host "Local proxy 127.0.0.1:7897 is not listening; pushing without proxy."
  Run-Git push origin main
} else {
  Write-Host "Pushing through local proxy..."
  $env:GCM_INTERACTIVE = "Never"
  Run-Git -c "credential.username=$githubUser" -c "credential.interactive=never" -c "http.proxy=$proxy" -c "https.proxy=$proxy" push origin main
}

Write-Host "Push completed."
Run-Git status -sb
Run-Git log -1 --oneline --decorate
