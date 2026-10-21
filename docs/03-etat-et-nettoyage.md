# 3. État et nettoyage proposé

[Retour au guide principal](../README.md)

> État historique antérieur à la migration. Le port Community est désormais
> déployé dans `addons/`, avec les originaux conservés. Voir le
> [rapport de migration actuel](MIGRATION_COMMUNITY.md) pour l'état vérifié.

## État vérifié le 20 octobre 2026

Instance : http://127.0.0.1:8073 ; base food_distribution ; Odoo 19 Community.
Les cinq applications du MVP sont installées. Les 76 modules installés déclarent une licence LGPL-3. Les paquets food_distribution et base_industry_data sont non installés.
Société : StockPro Demo ; pays : MR ; entrepôt : Dépôt principal (WH).
La devise actuelle est USD : le réglage MRU reste à corriger et valider.

## Réalisé

Ajout du README principal et de trois guides français : organisation, démarrage, données persistantes, vocabulaire et circuit commercial à tester. Aucun original supprimé ; configuration Docker et données Odoo inchangées par cette documentation.

## Nettoyage préparé, non exécuté

- Archiver puis retirer les dossiers Enterprise non utilisés food_distribution, base_industry_data et enterprise, avec leurs ressources statiques et traductions.
- Retirer l'ancien outil docker/install_community.py et le README.docker.md remplacé par les nouveaux guides.
- Créer addons comme emplacement pour d'éventuels modules futurs.
- Adapter les montages dans compose.yaml et le chemin des modules dans docker/odoo.conf.
- Recréer uniquement le conteneur Odoo en conservant le nom du projet et les volumes existants ; vérifier ensuite la connexion.

Ce changement peut interrompre brièvement l'accès à Odoo. La revue automatique a refusé son exécution : la suppression de dossiers complets et la modification Docker dépassent une simple suppression de fichiers statiques superflus. Un accord explicite sur ce périmètre est attendu.

Les fichiers préparés sont dans C:\Users\x1\Desktop\StockPro\reorganisation-projet. Le script de nettoyage n'a pas été exécuté. L'archive des originaux n'a donc pas encore été créée.

## Pourquoi ne pas supprimer seulement static ?

Les images et le JavaScript des paquets fournis sont référencés par leurs données XML ou leurs manifestes. Les effacer isolément laisserait des paquets incomplets. Retirer les paquets non installés avec leurs montages est plus cohérent, après archivage et accord sur ce périmètre.
