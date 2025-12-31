package acgs.rbac

# RBAC Policy - Stricter least-privilege, tenant-scoped (ACGS-2 Enhanced)
# NIST 800-53 AC-6, OWASP A01:2021 Broken Access Control
# Constitutional Hash: cdd01ef066bc6cf2
# P99 eval <5ms: simple array membership checks

default allow := false

# Allow if user has required role in tenant context
allow {
	input.user.roles[_] == input.required_role
	input.user.tenant_id == input.tenant_id
	input.constitutional_hash == "cdd01ef066bc6cf2"
	not privilege_escalation_attempt
}

# Deny privilege escalation (stricter)
privilege_escalation_attempt {
	input.required_role == "admin"
	input.user.roles[_] != "admin"
}

privilege_escalation_attempt {
	input.action == "delete"
	input.user.roles[_] != "admin"
	input.user.roles[_] != "owner"
}

# Input validation: roles array non-empty, strings only (OWASP Injection prev)
valid_roles {
	is_array(input.user.roles)
	count(input.user.roles) > 0
	input.user.roles[_] matches "^[a-zA-Z0-9_-]+$"
}

# Metrics: RBAC denials
violation[msg] {
	not allow
	msg := sprintf("RBAC denial: role '%v' insufficient for '%v' in tenant '%v'", [input.required_role, input.action, input.tenant_id])
}