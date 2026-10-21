# Odoo avec Docker

> Guide historique. La migration Community est maintenant appliquée ; lire
> [le README actuel](README.md) et [le rapport de migration](docs/MIGRATION_COMMUNITY.md).
> Les indications Enterprise ci-dessous concernent les paquets d'origine conservés.

Cette configuration utilise deux services : Odoo 19 et PostgreSQL 15.
Les donnees sont conservees dans des volumes Docker. PostgreSQL est accessible
uniquement depuis le reseau Docker du projet.

## Demarrage

La configuration locale `.env` et `docker/odoo.conf` contient les mots de passe
generes pour cette installation. Conserver ces fichiers localement.

```powershell
docker compose up -d
docker compose ps
```

Ouvrir http://localhost:8073 (ou le port ODOO_PORT indique dans `.env`).
Les identifiants locaux sont dans `.env` : ODOO_LOGIN et ODOO_PASSWORD.
Le mot de passe maitre de gestion des bases est dans `docker/odoo.conf`.

## Applications Community

Les applications gratuites utilisees pour cette installation sont Ventes
(`sale_management`), Achats (`purchase`), Inventaire (`stock`), Fabrication
(`mrp`), Facturation (`account`) et Dates de peremption (`product_expiry`).
Elles proposent les fonctions metier standard. Le module sectoriel
Food Distribution reste distinct et necessite ses dependances Enterprise.

Le script `docker/install_community.py` installe ces applications via l'API
Odoo authentifiee et verifie leur etat. Il utilise la variable
`ODOO_SETUP_PASSWORD` sans afficher sa valeur.

## Module Food Distribution et Enterprise

Les deux modules du dossier sont montes dans le conteneur Odoo.
Food Distribution depend de modules Odoo Enterprise qui ne sont pas fournis
dans ce dossier ni dans l'image officielle Odoo Community.

Pour activer Food Distribution, placer les modules Enterprise compatibles Odoo 19
obtenus avec votre acces Odoo dans `enterprise/` (un dossier par module), puis :

```powershell
docker compose restart odoo
```

Dans Odoo, activer le mode developpeur, actualiser la liste des applications,
puis installer Food Distribution une fois toutes ses dependances presentes.

## Gestion

```powershell
docker compose logs --tail=100 odoo
docker compose stop
docker compose start
docker compose down
```

`docker compose down` conserve les volumes. L'option `-v` supprime les donnees.
