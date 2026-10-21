# Grossiste Odoo â€” Odoo 19 Community

Version finale migrÃ©e vers lâ€™architecture standard Odoo. Le code livrÃ© se trouve
dans **`addons/`** et utilise les modules natifs Community ainsi que le module OCA
non modifiÃ© dans **`vendor/`**.

Ouvrir **http://localhost:8073** aprÃ¨s avoir crÃ©Ã© `.env` depuis `.env.example`.

Les modules livrÃ©s sont :

- `food_distribution/` : `models/`, `views/`, `security/`, `data/`, `report/`, `demo/`, `tests/`.
- `base_industry_data/` : socle Community.
- `food_distribution_quality/` : intÃ©gration MRP et qualitÃ© OCA.
- `food_distribution_planning/` : prÃ©visions manuelles utilisant les OF standards.

Le composant tiers non modifiÃ© est dans `vendor/quality_control_oca/`.
Les applications Ventes, Achats, Inventaire, Fabrication et Facturation restent natives.

```powershell
Copy-Item .env.example .env
docker compose up -d
docker compose ps
docker compose logs --tail=100 odoo
```

Les donnÃ©es restent dans PostgreSQL et les volumes Docker existants. Ne pas utiliser
`docker compose down -v` pour un simple arrÃªt : cela supprimerait les volumes.

Lire le [rapport de migration et les Ã©carts Enterprise](docs/MIGRATION_COMMUNITY.md)
et le [rapport de prÃ©paration production](docs/PRODUCTION_READINESS.md).
Les preuves de validation sont dans `docs/evidence/`.

