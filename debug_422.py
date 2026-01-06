import os
import sys
import traceback

from fastapi.testclient import TestClient

# Ensure src and service dir are in pythonpath
sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("src/core/services/api_gateway"))

from main import app


def debug_422():
    client = TestClient(app, raise_server_exceptions=True)
    # Reset SAML handler to ensure it initializes with current settings
    import routes.sso as sso_module

    sso_module._saml_handler = None

    print("Testing /sso/saml/login?provider=okta")
    try:
        response = client.get("/sso/saml/login?provider=okta")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 422:
            print(f"Detail: {response.json()}")
    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    debug_422()
