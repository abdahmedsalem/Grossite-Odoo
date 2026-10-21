# Grossiste Odoo — Odoo 19 Community

Version finale migrée vers l’architecture standard Odoo. Le code livré se trouve
dans **`addons/`** et utilise les modules natifs Community ainsi que le module OCA
non modifié dans **`vendor/`**.

Ouvrir **http://localhost:8073** après avoir créé `.env` depuis `.env.example`.

Les modules livrés sont :

- `food_distribution/` : `models/`, `views/`, `security/`, `data/`, `report/`, `demo/`, `tests/`.
- `base_industry_data/` : socle Community.
- `food_distribution_quality/` : intégration MRP et qualité OCA.
- `food_distribution_planning/` : prévisions manuelles utilisant les OF standards.

Le composant tiers non modifié est dans `vendor/quality_control_oca/`.
Les applications Ventes, Achats, Inventaire, Fabrication et Facturation restent natives.

```powershell
Copy-Item .env.example .env
docker compose up -d
docker compose ps
docker compose logs --tail=100 odoo
```

Les données restent dans PostgreSQL et les volumes Docker existants. Ne pas utiliser
`docker compose down -v` pour un simple arrêt : cela supprimerait les volumes.

Lire le [rapport de migration et les écarts Enterprise](docs/MIGRATION_COMMUNITY.md)
et le [rapport de préparation production](docs/PRODUCTION_READINESS.md).
Les preuves de validation sont dans `migration/evidence/`.
