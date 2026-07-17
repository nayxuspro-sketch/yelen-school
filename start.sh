#!/bin/bash
# YELEN SCHOOL - Script de demarrage

COMPOSE="docker compose -f docker-compose.dev.yml"

case "$1" in
    start)
        $COMPOSE up
        ;;
    start-bg)
        $COMPOSE up -d
        ;;
    stop)
        $COMPOSE down
        ;;
    build)
        $COMPOSE up --build
        ;;
    restart)
        $COMPOSE restart web
        ;;
    logs)
        $COMPOSE logs -f
        ;;
    logs-web)
        $COMPOSE logs -f web
        ;;
    migrate)
        $COMPOSE run --rm web python manage.py migrate
        ;;
    shell)
        $COMPOSE run --rm web python manage.py shell
        ;;
    superuser)
        $COMPOSE run --rm web python manage.py createsuperuser
        ;;
    admin)
        $COMPOSE run --rm web python manage.py ensure_admin
        ;;
    bash)
        $COMPOSE run --rm web bash
        ;;
    *)
        echo "Usage: ./start.sh {start|start-bg|stop|build|restart|logs|logs-web|migrate|shell|superuser|admin|bash}"
        echo ""
        echo "  start       - Demarrer tout (foreground)"
        echo "  start-bg    - Demarrer en arriere-plan"
        echo "  stop        - Arreter tout"
        echo "  build       - Builder et demarrer"
        echo "  restart     - Redemarrer web"
        echo "  logs        - Voir les logs"
        echo "  logs-web    - Voir les logs web"
        echo "  migrate     - Appliquer les migrations"
        echo "  shell       - Shell Django"
        echo "  superuser   - Creer un superuser"
        echo "  admin       - Creer/Reinitialiser le super admin par defaut"
        echo "  bash        - Entrer dans le conteneur"
        ;;
esac
