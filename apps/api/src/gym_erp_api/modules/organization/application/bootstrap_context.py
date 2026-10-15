"""Identificadores internos para alta sin actor autenticado (ADR-0003 Proposed).

No constituyen autorización criptográfica; solo permiten construir TenantContext
válido durante bootstrap organizacional.
"""

CREATE_ORGANIZATION_BOOTSTRAP_USER_ID = "00000000-0000-4000-8000-000000000001"
CREATE_ORGANIZATION_BOOTSTRAP_MEMBERSHIP_ID = "00000000-0000-4000-8000-000000000002"
