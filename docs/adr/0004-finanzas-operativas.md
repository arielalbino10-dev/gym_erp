# ADR-0004: Finanzas operativas (alcance)

- **Estado:** Accepted (alcance y principios). Reglas detalladas: **Proposed** (pendientes listadas abajo).
- **Fecha:** 2026-10-13 (documentación H0-A)
- **Decisores:** Propietario del producto

## Contexto

Los gimnasios necesitan registrar adeudos y cobros (membresías, servicios) con trazabilidad.
Release 0.1 **no** incluye contabilidad formal (partida doble, pólizas, catálogo de cuentas)
ni facturación electrónica (CFDI). Las reglas de seguridad exigen idempotencia en pagos,
movimientos auditables, transacciones cuando corresponda y no eliminar historiales financieros.

## Decisión (alcance aprobado)

1. **Modelo operativo**, no contable:
   - **Cargo (Charge):** obligación de pago de un miembro (monto, moneda, vencimiento, estado).
   - **Pago (Payment):** ingreso registrado (efectivo, transferencia, terminal externa, etc.).
   - **Aplicación (Allocation):** vínculo de cuánto de un pago cubre qué cargo(s).
   - **Devolución / reversa (Refund / Reversal):** corrección mediante **nuevo movimiento**;
     no borrado ni edición de montos en registros existentes.
   - **Auditoría financiera:** eventos append-only ligados a operaciones sensibles.
2. **Inmutabilidad:** no DELETE en registros financieros; correcciones vía reversas/compensaciones.
3. **Idempotencia** obligatoria al crear pagos (clave por tenant).
4. **Atomicidad:** operaciones que tocan cargo + pago + aplicaciones + auditoría en **una
   transacción MongoDB** (replica set requerido).
5. **Fuera de alcance 0.1:** contabilidad formal, CFDI, conciliación bancaria automática,
   pasarela de pago integrada (hipótesis futura).

## Alternativas consideradas

- **Solo registrar pagos sin cargos:** no permite adeudos ni bitácora de cobranza; descartado.
- **Contabilidad completa desde 0.1:** complejidad no justificada para piloto; descartado.
- **Borrado de pagos erróneos:** contradice reglas de auditoría; descartado.

## Consecuencias

- UI y API hablan de **cobros operativos**, no de “asientos contables”.
- Base extensible hacia contabilidad/CFDI con ADR futuros.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Confundir operativo con contabilidad | Naming en UI/docs; ADR explícito |
| Pagos duplicados | Idempotencia + índice único (tenant, key) |
| Inconsistencia sin transacciones | Replica set + tests de integración |
| Detalle no definido obliga a migraciones | Cerrar pendientes antes de implementar pagos |

## Controles verificables

- Tests: idempotencia, transacción abortada, prohibición de DELETE, aislamiento entre tenants.
- Endpoints sin DELETE para entidades financieras.
- Montos validados en backend (pendiente ADR-0006 para representación).

## Condiciones de revisión

- Alcance contable o CFDI aprobado por negocio.
- Integración con pasarela o facturación externa.

## Reglas detalladas — Proposed (no aprobadas aún)

- Modelo exacto de aplicación parcial (1:1, 1:N, N:1).
- Estados y transiciones de Charge y Payment.
- Descuentos, promociones, impuestos informativos.
- Corte de caja / turno de recepción en 0.1 vs 0.2.
- Cálculo de saldo (consulta vs snapshot materializado).
- Permisos por rol (`payments:create`, `payments:reverse`, etc.).
- Formato y TTL de `Idempotency-Key`.
- Moneda por tenant (MXN en piloto México — confirmar en ADR-0006).
