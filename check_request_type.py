import os
import sys

# Add api_gateway to path
sys.path.insert(0, os.path.abspath("src/core/services/api_gateway"))
# Add src to path
sys.path.append(os.path.abspath("src"))

from fastapi import Request

from main import app

print(f"FastAPI Request class: {Request}")

for route in app.routes:
    if hasattr(route, "path") and "/sso/saml/login" in route.path:
        print(f"Route: {route.path}")
        # Look for the parameter name 'request' in any of the dependant's attributes
        d = route.dependant
        print(f"  Query Params: {[p.name for p in d.query_params]}")

        # Check if 'request' is in query_params
        for p in d.query_params:
            if p.name == "request":
                print(f"!!! FOUND 'request' IN QUERY PARAMS for {route.path}")
                print(f"  Type: {p.type_}")

        # Check where 'request' is
        for p in d.path_params:
            if p.name == "request":
                print("  'request' in path_params")

        # Check if 'request' is a body param
        if d.body_params:
            for p in d.body_params:
                if p.name == "request":
                    print("  'request' in body_params")

        # FastAPI should have it in d.request_param_name
        if hasattr(d, "request_param_name"):
            print(f"  request_param_name: {d.request_param_name}")
        else:
            print("  No request_param_name attribute")
