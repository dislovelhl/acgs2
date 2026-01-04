# Simple valid Rego policy for E2E testing
package test.valid

import rego.v1

default allow := false

# Allow if the user is an admin
allow if {
    input.user.role == "admin"
}

# Allow if the request method is GET
allow if {
    input.request.method == "GET"
    input.user.authenticated == true
}
