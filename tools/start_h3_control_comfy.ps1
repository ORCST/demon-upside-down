# H3 Fun ControlNet on this Windows installation needs the compiler workaround.
$ErrorActionPreference = 'Stop'
$controlProjectPath = Split-Path -Parent $PSScriptRoot
$controlAuditPath = Join-Path $controlProjectPath 'outputs/h3_control_setup_20261015'
$controlInstallPath = 'D:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI'
try {
    $controlServer = Invoke-RestMethod -Uri 'http://127.0.0.1:8189/system_stats' -TimeoutSec 2
    Write-Output "ComfyUI already listening on 8189 (version $($controlServer.system.comfyui_version)); no second process started."
    exit 0
} catch [System.Net.Http.HttpRequestException] {
    # No local server; start this project's instance.
} catch [System.Threading.Tasks.TaskCanceledException] {
    throw 'Port 8189 did not answer; check the existing process before starting another.'
}
foreach ($controlFolder in @('comfy_input','comfy_output','comfy_user')) {
    New-Item -ItemType Directory -Path (Join-Path $controlAuditPath $controlFolder) -Force | Out-Null
}
$controlArguments = @('main.py','--listen','127.0.0.1','--port','8189',
    '--models-directory','D:/Comfy-Desktop/ComfyUI-Shared/models',
    '--input-directory',(Join-Path $controlAuditPath 'comfy_input'),
    '--output-directory',(Join-Path $controlAuditPath 'comfy_output'),
    '--user-directory',(Join-Path $controlAuditPath 'comfy_user'),
    '--disable-auto-launch','--disable-all-custom-nodes','--disable-api-nodes',
    '--use-pytorch-cross-attention','--preview-method','none','--disable-comfy-compiler')
$comfyControlProcess = Start-Process -FilePath (Join-Path $controlInstallPath '.venv/Scripts/python.exe') `
    -WorkingDirectory $controlInstallPath -ArgumentList $controlArguments -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $controlAuditPath 'comfy_launcher_stdout.log') `
    -RedirectStandardError (Join-Path $controlAuditPath 'comfy_launcher_stderr.log') -PassThru
$comfyControlProcess.Id | Set-Content -LiteralPath (Join-Path $controlAuditPath 'comfy_pid.txt')
Write-Output "Started project ComfyUI process $($comfyControlProcess.Id), compiler disabled."
