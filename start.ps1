# YELEN SCHOOL - Script de demarrage

param(
    [string]$cmd = "start"
)

$COMPOSE = "docker compose -f docker-compose.dev.yml"

switch ($cmd) {
    "start"      { & $COMPOSE up }
    "start-bg"   { & $COMPOSE up -d }
    "stop"       { & $COMPOSE down }
    "build"      { & $COMPOSE up --build }
    "restart"    { & $COMPOSE restart web }
    "logs"       { & $COMPOSE logs -f }
    "logs-web"   { & $COMPOSE logs -f web }
    "migrate"    { & $COMPOSE run --rm web python manage.py migrate }
    "shell"      { & $COMPOSE run --rm web python manage.py shell }
    "superuser"  { & $COMPOSE run --rm web python manage.py createsuperuser }
    "bash"       { & $COMPOSE run --rm web bash }
    default {
        Write-Host "用法 (Usage):" -ForegroundColor Cyan
        Write-Host "  .\start.ps1 start       - Demarrer tout (foreground)"
        Write-Host "  .\start.ps1 start-bg    - Demarrer en arriere-plan"
        Write-Host "  .\start.ps1 stop        - Arreter tout"
        Write-Host "  .\start.ps1 build       - Builder et demarrer"
        Write-Host "  .\start.ps1 logs        - Voir les logs"
        Write-Host "  .\start.ps1 migrate    - Appliquer les migrations"
        Write-Host "  .\start.ps1 shell       - Shell Django"
        Write-Host "  .\start.ps1 superuser  - Creer un superuser"
        Write-Host "  .\start.ps1 bash       - Entrer dans le conteneur"
    }
}
