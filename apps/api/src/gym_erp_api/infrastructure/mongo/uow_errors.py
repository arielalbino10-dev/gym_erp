"""Errores de infraestructura para Unit of Work MongoDB."""


class MongoUnitOfWorkError(Exception):
    """Base para fallos al coordinar sesión/transacción MongoDB."""


class InvalidMongoSessionError(MongoUnitOfWorkError):
    """Sesión ausente, finalizada o de tipo incompatible."""


class MongoUnitOfWorkInactiveError(MongoUnitOfWorkError):
    """Operación sobre un Unit of Work que ya no está activo."""


class MongoTransactionCommitUncertainError(MongoUnitOfWorkError):
    """Commit con resultado desconocido en el servidor (UnknownTransactionCommitResult).

    La operación de negocio pudo haberse aplicado o no. No implica rollback confirmado.
    H1-D.3.3+ debe reconciliar o reintentar según idempotencia; este módulo no reintenta.
    """
