param([string]$cmd = "dev")

$COMPOSE = "docker compose -f docker-compose.dev.yml"

switch ($cmd) {
    "dev"             { Invoke-Expression "$COMPOSE up" }
    "dev-bg"          { Invoke-Expression "$COMPOSE up -d" }
    "build"           { Invoke-Expression "$COMPOSE up --build" }
    "stop"            { Invoke-Expression "$COMPOSE down" }
    "restart"         { Invoke-Expression "$COMPOSE restart web" }
    "logs"            { Invoke-Expression "$COMPOSE logs -f" }
    "logs-web"        { Invoke-Expression "$COMPOSE logs -f web" }
    "migrate"         { Invoke-Expression "$COMPOSE run --rm web python manage.py migrate" }
    "makemigrations"  { Invoke-Expression "$COMPOSE run --rm web python manage.py makemigrations" }
    "shell"           { Invoke-Expression "$COMPOSE run --rm web python manage.py shell" }
    "createsuperuser" { Invoke-Expression "$COMPOSE run --rm web python manage.py createsuperuser" }
    "admin"           { Invoke-Expression "$COMPOSE run --rm web python manage.py ensure_admin" }
    "bash"            { Invoke-Expression "$COMPOSE run --rm web bash" }
    "psql"            { Invoke-Expression "$COMPOSE exec db psql -U yelen_user -d yelen_school_db" }
    default {
        Write-Host "Commandes disponibles :"
        Write-Host "  .\dev.ps1 dev              - Demarrer tout"
        Write-Host "  .\dev.ps1 build            - Rebuilder + demarrer"
        Write-Host "  .\dev.ps1 stop             - Arreter tout"
        Write-Host "  .\dev.ps1 migrate          - Appliquer les migrations"
        Write-Host "  .\dev.ps1 makemigrations   - Creer des migrations"
        Write-Host "  .\dev.ps1 logs             - Voir les logs"
        Write-Host "  .\dev.ps1 shell            - Shell Django"
        Write-Host "  .\dev.ps1 admin            - Creer/Reinitialiser le super admin par defaut"
        Write-Host "  .\dev.ps1 psql             - Console PostgreSQL"
        Write-Host "  .\dev.ps1 bash             - Bash dans le conteneur web"
    }
}
