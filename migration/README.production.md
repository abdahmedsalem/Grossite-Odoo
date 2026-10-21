# StockPro Alimentaire — Odoo 19 Community

Ouvrir **http://localhost:8073**. Les identifiants existants restent dans `.env`.

Le code actif utilise maintenant une architecture standard Odoo dans **`addons/`** :

- `food_distribution/` : `models/`, `views/`, `security/`, `data/`, `report/`, `demo/`, `tests/`.
- `base_industry_data/` : socle Community.
- `food_distribution_quality/` : intégration MRP et qualité OCA.
- `food_distribution_planning/` : prévisions manuelles utilisant les OF standards.

Le composant tiers non modifié est dans `vendor/quality_control_oca/`.
Les applications Ventes, Achats, Inventaire, Fabrication et Facturation restent natives.

Les dossiers historiques `food_distribution/` et `base_industry_data/` à la racine
sont conservés comme références ; ils ne sont plus montés dans l'instance active.
Ne pas y faire les développements futurs.

```powershell
docker compose up -d
docker compose ps
docker compose logs --tail=100 odoo
```

Les données restent dans PostgreSQL et les volumes Docker existants. Ne pas utiliser
`docker compose down -v` pour un simple arrêt : cela supprimerait les volumes.

Lire le [rapport de migration et les écarts Enterprise](docs/MIGRATION_COMMUNITY.md)
pour connaître précisément les fonctions réutilisées, portées et non équivalentes.
Les preuves et captures sont dans `migration/evidence/`, les sauvegardes privées dans
`backups/`. Les exemples de test ne sont pas importés dans la base utilisateur.

La prévisualisation isolée, lorsqu'elle est démarrée, est sur **http://localhost:8074**.
La documentation historique `docs/01-*`, `docs/02-*`, `docs/03-*` décrit l'état
antérieur ; le rapport de migration prévaut pour l'organisation actuelle.
