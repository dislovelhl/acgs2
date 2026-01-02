# Invalid Rego policy with syntax errors for E2E testing
package test.invalid

default allow = false

# Missing closing brace
allow {
    input.user.role == "admin"

# Invalid syntax - missing operator
allow if input.user.role "admin"
