"""Catálogo cerrado de permisos platform (consola SaaS Gym ERP)."""

from __future__ import annotations

from enum import StrEnum

PLATFORM_PERMISSION_CATALOG_VERSION = "2026-04-h3a3-mvp"


class PlatformPermission(StrEnum):
    COMMERCIAL_PLANS_READ = "commercial.plans.read"
    COMMERCIAL_PLANS_CREATE = "commercial.plans.create"
    COMMERCIAL_PLANS_UPDATE = "commercial.plans.update"
    COMMERCIAL_PLANS_PUBLISH = "commercial.plans.publish"
    COMMERCIAL_REQUESTS_READ = "commercial.requests.read"
    COMMERCIAL_REQUESTS_REVIEW = "commercial.requests.review"
    COMMERCIAL_REQUESTS_APPROVE = "commercial.requests.approve"
    COMMERCIAL_REQUESTS_REJECT = "commercial.requests.reject"
    COMMERCIAL_PAYMENTS_READ = "commercial.payments.read"
    COMMERCIAL_PAYMENTS_RECORD = "commercial.payments.record"
    COMMERCIAL_PAYMENTS_VERIFY = "commercial.payments.verify"
    COMMERCIAL_CLIENTS_READ = "commercial.clients.read"
    COMMERCIAL_CLIENTS_MANAGE = "commercial.clients.manage"
    COMMERCIAL_SUBSCRIPTIONS_READ = "commercial.subscriptions.read"
    COMMERCIAL_SUBSCRIPTIONS_MANAGE = "commercial.subscriptions.manage"
    PLATFORM_OPERATORS_READ = "platform.operators.read"
    PLATFORM_OPERATORS_MANAGE = "platform.operators.manage"
    PLATFORM_AUDIT_READ = "platform.audit.read"
    PLATFORM_SYSTEM_READ = "platform.system.read"


ALL_PLATFORM_PERMISSIONS: frozenset[PlatformPermission] = frozenset(PlatformPermission)
