COMPOSE = docker-compose -f docker-compose.dev.yml

.PHONY: dev build stop restart logs shell migrate makemigrations createsuperuser

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

## Ouvrir un shell bash dans le conteneur web
bash:
	$(COMPOSE) exec web bash

## Ouvrir psql dans le conteneur db
psql:
	$(COMPOSE) exec db psql -U yelen_user -d yelen_school_db
