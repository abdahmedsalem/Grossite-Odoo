# Ã‰tat de prÃ©paration production

## ContrÃ´les rÃ©alisÃ©s

- Odoo 19 et PostgreSQL 15 sont dÃ©marrÃ©s avec des conteneurs `healthy`.
- Lâ€™interface `http://localhost:8073/web/login?db=food_distribution` rÃ©pond HTTP 200.
- Les modules `food_distribution`, `food_distribution_planning`,
  `food_distribution_quality` et `quality_control_oca` sont installÃ©s.
- Les contrÃ´les dâ€™architecture standard passent : 137 vÃ©rifications.
- Les tests Odoo de migration sÃ©lectionnÃ©s passent : 18 tests, 0 Ã©chec, 0 erreur.
- Les parcours navigateur et la conservation des donnÃ©es sont documentÃ©s dans
  `docs/evidence/`.
- Une sauvegarde de la base et du filestore existe dans
  `backups/pre-community-20261020-145921/`.
- Le port Odoo est limitÃ© Ã  `127.0.0.1:8073`; PostgreSQL nâ€™est pas publiÃ© sur
  lâ€™hÃ´te.

## Conditions avant exposition publique

Avant dâ€™ouvrir le service sur Internet, lâ€™exploitant doit :

1. remplacer les valeurs de `.env` par des secrets propres Ã  lâ€™environnement ;
2. placer Odoo derriÃ¨re un proxy HTTPS avec un nom de domaine et des certificats ;
3. planifier les sauvegardes PostgreSQL et du filestore, puis effectuer un test
   de restauration sur une copie isolÃ©e ;
4. configurer la supervision des conteneurs, de lâ€™espace disque et des erreurs ;
5. crÃ©er les comptes utilisateurs rÃ©els et dÃ©sactiver les comptes de test.

Ces mesures sont opÃ©rationnelles et ne nÃ©cessitent pas de modifier le code Odoo.

