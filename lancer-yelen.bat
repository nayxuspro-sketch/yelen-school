@echo off
chcp 65001 >nul
E:
cd yelen-school
docker compose -f docker-compose.dev.yml up -d
echo Application lancée !
start http://localhost:8000/accounts/login/?next=/
exit