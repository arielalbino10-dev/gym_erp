import Modal from "../ui/Modal.jsx";
import Badge from "../ui/Badge.jsx";
import Button from "../ui/Button.jsx";
import { branchStatusBadgeVariant, branchStatusLabel } from "../../demo/branches.demo.js";

export default function BranchDetailModal({
  branch,
  memberCount,
  onClose,
  statusLabel,
  statusVariant,
}) {
  if (!branch) {
    return null;
  }

  return (
    <Modal
      isOpen={Boolean(branch)}
      title={`Sucursal — ${branch.branchCode}`}
      onClose={onClose}
      footer={
        <Button type="button" variant="primary" onClick={onClose}>
          Cerrar
        </Button>
      }
    >
      <dl className="detail-dl">
        <div className="detail-dl__row">
          <dt>Nombre</dt>
          <dd>{branch.name}</dd>
        </div>
        <div className="detail-dl__row">
          <dt>Código</dt>
          <dd>
            <code>{branch.branchCode}</code>
          </dd>
        </div>
        <div className="detail-dl__row">
          <dt>Identificador</dt>
          <dd>
            <code>{branch.branchId}</code>
          </dd>
        </div>
        <div className="detail-dl__row">
          <dt>Estado</dt>
          <dd>
            <Badge variant={statusVariant || branchStatusBadgeVariant(branch.status)}>
              {statusLabel || branchStatusLabel(branch.status)}
            </Badge>
          </dd>
        </div>
        {branch.locationLabel ? (
          <div className="detail-dl__row">
            <dt>Zona horaria / ubicación</dt>
            <dd>{branch.locationLabel}</dd>
          </div>
        ) : null}
        {memberCount > 0 ? (
          <div className="detail-dl__row">
            <dt>Socios asignados (demo)</dt>
            <dd>{memberCount}</dd>
          </div>
        ) : null}
        {branch.description ? (
          <div className="detail-dl__row">
            <dt>Descripción</dt>
            <dd>{branch.description}</dd>
          </div>
        ) : null}
      </dl>
    </Modal>
  );
}
