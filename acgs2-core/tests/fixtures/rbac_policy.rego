# RBAC policy for E2E testing with evaluation
package test.rbac

import rego.v1

default allow := false

# Admins can do anything
allow if {
    input.role == "admin"
}

# Editors can read and write
allow if {
    input.role == "editor"
    input.action == "read"
}

allow if {
    input.role == "editor"
    input.action == "write"
}

# Viewers can only read
allow if {
    input.role == "viewer"
    input.action == "read"
}

# Reason for the decision
reason := msg if {
    allow
    msg := sprintf("Access granted for role '%s' with action '%s'", [input.role, input.action])
}

reason := msg if {
    not allow
    msg := sprintf("Access denied for role '%s' with action '%s'", [input.role, input.action])
}
