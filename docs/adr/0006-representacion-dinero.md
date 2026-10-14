# ADR-0006: Representación de importes monetarios

- **Estado:** Proposed
- **Fecha:** 2026-10-13 (documentación H0-A)
- **Decisores:** Propietario del producto (aprobación pendiente)

## Contexto

ADR-0004 define cargos y pagos operativos. Los importes deben persistirse y transmitirse
sin errores de redondeo. El stack incluye Python, JavaScript (`.jsx`) y MongoDB. En el
piloto México se espera **MXN**, pero la representación debe alinearse con **ISO 4217**
(unidades menores por moneda, no asumir siempre “centavos” como nombre de campo).

## Decisión (propuesta)

1. Almacenar importes como **enteros en unidades menores** de la moneda (p. ej. centavos
   para MXN con 2 decimales), junto con código **`currency`** ISO 4217 (p. ej. `MXN`).
2. Contrato API (nombres exactos pendientes): p. ej. `amount_minor` (integer) + `currency` (string).
3. Backend: tipo de valor `Money` (inmutable) con aritmética entera; prohibido `float` en
   dominio, persistencia y respuestas API para importes.
4. Frontend: formateo con `Intl.NumberFormat`; conversión de entrada de usuario a unidades
   menores; **no** calcular totales de negocio en el cliente.
5. Una moneda por tenant en piloto (decisión de producto); multimoneda = revisión futura.

## Alternativas consideradas

- **Decimal128 + Decimal en Python:** precisión decimal; en JS requiere strings/librería.
- **String decimal en API:** seguro; más propenso a errores de parsing.
- **Float:** descartado.

## Consecuencias

- Contrato claro para web y futuro móvil.
- Reglas de redondeo necesarias para descuentos/impuestos porcentuales (pendiente).

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Error al parsear input usuario | Tests de conversión; validación Pydantic |
| Monedas con decimales ≠ 2 | Tabla ISO; fuera de alcance hasta multimoneda |
| Implementar pagos antes de aprobar ADR-0006 | Bloquear E0.8–E0.9 hasta Accepted |

## Controles verificables

- Rechazo de floats en schemas financieros.
- Tests unitarios de `Money` y casos límite.

## Condiciones de revisión

- Aprobación explícita del propietario.
- Requisito de sub-unidad de centavo o multimoneda.

## Pendiente de aprobación

- Nombres finales de campos en API.
- Regla de redondeo (half-up, etc.) y dónde se aplica.
- Confirmación MXN única por tenant en 0.1.
