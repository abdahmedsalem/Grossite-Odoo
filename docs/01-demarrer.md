# 1. Utiliser l’installation locale

[Retour au guide principal](../README.md)

## Avant de commencer

Docker Desktop doit être démarré. Dans l’Explorateur Windows, ouvrir le dossier du projet, puis ouvrir PowerShell dans ce dossier. Les commandes suivantes utilisent le fichier `compose.yaml` présent ici.

## Commandes utiles

| Action | Commande PowerShell |
| --- | --- |
| Démarrer Odoo et PostgreSQL | `docker compose up -d` |
| Voir leur état | `docker compose ps` |
| Lire les derniers messages Odoo | `docker compose logs --tail=80 odoo` |
| Arrêter temporairement | `docker compose stop` |
| Relancer après un arrêt | `docker compose start` |
| Redémarrer Odoo après un changement de sa configuration | `docker compose restart odoo` |

Après un changement de `compose.yaml`, utiliser `docker compose up -d` pour appliquer la configuration des conteneurs.

## Ouvrir Odoo

Adresse : http://127.0.0.1:8073.

Base : `food_distribution`. Les accès locaux existants sont dans `.env`. Modifier ce fichier ne change pas automatiquement le mot de passe d’un utilisateur déjà créé dans Odoo.

## Où sont mes données ?

Docker conserve deux volumes nommés, indépendants des dossiers de modules :

| Volume réel | Contenu |
| --- | --- |
| `food-distribution_postgres-data` | Base PostgreSQL : contacts, produits, documents, paramètres |
| `food-distribution_odoo-data` | Fichiers joints et autres fichiers persistants d’Odoo |

Le nom de projet `food-distribution` dans `compose.yaml` permet de retrouver ces volumes. Le modifier ferait utiliser d’autres volumes par défaut.

Pour un arrêt ordinaire, utiliser `docker compose stop`. L’option `docker compose down -v` supprime les volumes : elle ne doit pas servir à arrêter cette installation.

La sauvegarde précédant la phase 1 se trouve dans `C:\Users\x1\Desktop\StockPro\backups` : un fichier `.dump` PostgreSQL et une archive du filestore. Elle correspond à l’état avant configuration, pas à une sauvegarde quotidienne à jour.

## Si la page ne s’ouvre pas

1. Vérifier que Docker Desktop fonctionne.
2. Exécuter `docker compose ps` dans le dossier du projet.
3. Démarrer avec `docker compose up -d`, puis attendre le démarrage d’Odoo.
4. Lire les logs avec la commande du tableau si le problème persiste.

PostgreSQL est accessible uniquement sur le réseau Docker du projet. Aucun port PostgreSQL n’est publié par cette configuration.
