COMPOSE = docker compose -f docker-compose.dev.yml

.PHONY: dev build stop restart logs shell migrate makemigrations createsuperuser admin

## Démarrer tous les services
dev:
	$(COMPOSE) up

## Démarrer en arrière-plan
dev-bg:
	$(COMPOSE) up -d

## Rebuilder les images puis démarrer
build:
	$(COMPOSE) up --build

## Arrêter tous les services
stop:
	$(COMPOSE) down

## Redémarrer le serveur web uniquement
restart:
	$(COMPOSE) restart web

## Voir les logs (tous les services)
logs:
	$(COMPOSE) logs -f

## Voir les logs du serveur web uniquement
logs-web:
	$(COMPOSE) logs -f web

## Appliquer les migrations
migrate:
	$(COMPOSE) exec web python manage.py migrate

## Créer de nouvelles migrations
makemigrations:
	$(COMPOSE) exec web python manage.py makemigrations

## Ouvrir le shell Django
shell:
	$(COMPOSE) exec web python manage.py shell

## Créer un superutilisateur
createsuperuser:
	$(COMPOSE) exec web python manage.py createsuperuser

## Vérifier/créer le super admin avec INITIAL_ADMIN_PASSWORD (sans réinitialisation implicite)
admin:
	$(COMPOSE) exec web python manage.py ensure_admin

## Réinitialiser explicitement le super admin avec INITIAL_ADMIN_PASSWORD
admin-reset:
	$(COMPOSE) exec web python manage.py ensure_admin --reset

## Ouvrir un shell bash dans le conteneur web
bash:
	$(COMPOSE) exec web bash

## Ouvrir psql dans le conteneur db
psql:
	$(COMPOSE) exec db psql -U yelen_user -d yelen_school_db

## Lancer les tests unitaires (dans le conteneur web)
test:
	$(COMPOSE) exec web python -m pytest $(ARGS)

## Lancer les tests avec couverture
test-cov:
	$(COMPOSE) exec web python -m pytest --cov --cov-report=term --cov-report=html $(ARGS)

## Lancer les tests d'une app spécifique (ex: make test-app app=core)
test-app:
	$(COMPOSE) exec web python -m pytest $(app)/tests/ $(ARGS)

## Afficher l'IP locale (pour accès depuis le téléphone)
ip:
	@echo "Adresse locale :"; \
	ip route get 1 2>/dev/null | awk '{print $$7; exit}' || \
	ipconfig 2>/dev/null | grep -A1 "LAN sans fil" | grep "IPv4" | awk '{print $$NF}'

## Exporter le certificat auto-signé (à installer sur le téléphone)
export-cert:
	$(COMPOSE) cp nginx:/etc/nginx/certs/yelen.crt ./yelen-dev.crt
	@echo "Certificat exporté : yelen-dev.crt — installez-le sur votre téléphone"
