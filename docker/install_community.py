"""Install the Community business apps using Odoo's authenticated API.

Run inside the Odoo container with ODOO_SETUP_PASSWORD set to the admin password.
"""

import os
import xmlrpc.client


url = os.environ.get("ODOO_SETUP_URL", "http://127.0.0.1:8069")
database = "food_distribution"
login = os.environ.get("ODOO_SETUP_LOGIN", "admin")
password = os.environ["ODOO_SETUP_PASSWORD"]
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(database, login, password, {})
if not uid:
    raise RuntimeError("Administrator authentication failed")

models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")


def call(model, method, args, **kwargs):
    return models.execute_kw(database, uid, password, model, method, args, kwargs)


names = ["sale_management", "purchase", "stock", "mrp", "account", "product_expiry"]
modules = call(
    "ir.module.module", "search_read", [[("name", "in", names)]],
    fields=["name", "state"],
)
missing = set(names) - {module["name"] for module in modules}
if missing:
    raise RuntimeError(f"Modules not found: {sorted(missing)}")
pending = [module["id"] for module in modules if module["state"] != "installed"]
if pending:
    call("ir.module.module", "button_immediate_install", [pending])

modules = call(
    "ir.module.module", "search_read", [[("name", "in", names)]],
    fields=["name", "state"],
)
for module in modules:
    print(f"{module['name']}: {module['state']}", flush=True)
if any(module["state"] != "installed" for module in modules):
    raise RuntimeError("Some Community apps are not installed")

menus = call(
    "ir.ui.menu", "search_read", [[("parent_id", "=", False)]], fields=["name"],
)
print("Root menus: " + ", ".join(menu["name"] for menu in menus), flush=True)
