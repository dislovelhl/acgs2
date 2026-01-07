# Add Security Headers Middleware to FastAPI Services

## Overview

Multiple FastAPI services (integration-service, compliance-docs, observability dashboard) lack security headers middleware. Missing headers include Content-Security-Policy, X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security, X-XSS-Protection, and Referrer-Policy.

## Rationale

Security headers provide defense-in-depth against common web attacks including XSS, clickjacking, MIME sniffing, and downgrade attacks. Enterprise governance systems handling sensitive policy data require these protections to meet compliance requirements.

---
*This spec was created from ideation and is pending detailed specification.*
