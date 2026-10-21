# État de préparation production

## Contrôles réalisés

- Odoo 19 et PostgreSQL 15 sont démarrés avec des conteneurs `healthy`.
- L’interface `http://localhost:8073/web/login?db=food_distribution` répond HTTP 200.
- Les modules `food_distribution`, `food_distribution_planning`,
  `food_distribution_quality` et `quality_control_oca` sont installés.
- Les contrôles d’architecture standard passent : 137 vérifications.
- Les tests Odoo de migration sélectionnés passent : 18 tests, 0 échec, 0 erreur.
- Les parcours navigateur et la conservation des données sont documentés dans
  `migration/evidence/`.
- Une sauvegarde de la base et du filestore existe dans
  `backups/pre-community-20261020-145921/`.
- Le port Odoo est limité à `127.0.0.1:8073`; PostgreSQL n’est pas publié sur
  l’hôte.

## Conditions avant exposition publique

Avant d’ouvrir le service sur Internet, l’exploitant doit :

1. remplacer les valeurs de `.env` par des secrets propres à l’environnement ;
2. placer Odoo derrière un proxy HTTPS avec un nom de domaine et des certificats ;
3. planifier les sauvegardes PostgreSQL et du filestore, puis effectuer un test
   de restauration sur une copie isolée ;
4. configurer la supervision des conteneurs, de l’espace disque et des erreurs ;
5. créer les comptes utilisateurs réels et désactiver les comptes de test.

Ces mesures sont opérationnelles et ne nécessitent pas de modifier le code Odoo.
