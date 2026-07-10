# setup_ssh_servidor.ps1
# Habilita o OpenSSH Server neste PC (GPU) para acesso remoto via Tailscale/SSH.
# COMO USAR: clique com o botao direito -> "Executar com PowerShell" como ADMINISTRADOR,
# ou abra um PowerShell como Admin e rode:  .\setup_ssh_servidor.ps1

Write-Host "== 1. Instalando OpenSSH Server ==" -ForegroundColor Cyan
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

Write-Host "== 2. Iniciando o servico sshd ==" -ForegroundColor Cyan
Start-Service sshd

Write-Host "== 3. Inicio automatico no boot ==" -ForegroundColor Cyan
Set-Service -Name sshd -StartupType 'Automatic'

Write-Host "== 4. Regra de firewall (porta 22) ==" -ForegroundColor Cyan
if (-not (Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -DisplayName "OpenSSH Server (sshd)" `
        -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
    Write-Host "Regra de firewall criada." -ForegroundColor Green
} else {
    Write-Host "Regra de firewall ja existe." -ForegroundColor Green
}

Write-Host "== 5. Status final ==" -ForegroundColor Cyan
Get-Service sshd | Select-Object Name, Status, StartType

Write-Host ""
Write-Host "Pronto. Seu usuario de login para SSH e: $env:USERNAME" -ForegroundColor Yellow
Write-Host "Do outro computador (na mesma rede Tailscale):  ssh $env:USERNAME@<ip-tailscale-deste-pc>" -ForegroundColor Yellow
