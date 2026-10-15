import Modal from "../ui/Modal.jsx";
import Badge from "../ui/Badge.jsx";
import Button from "../ui/Button.jsx";
import { branchStatusBadgeVariant, branchStatusLabel } from "../../demo/branches.demo.js";

export default function BranchDetailModal({ branch, memberCount, onClose }) {
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
          <dt>Código demo</dt>
          <dd>
            <code>{branch.branchCode}</code>
          </dd>
        </div>
        <div className="detail-dl__row">
          <dt>ID demo</dt>
          <dd>
            <code>{branch.branchId}</code>
          </dd>
        </div>
        <div className="detail-dl__row">
          <dt>Estado</dt>
          <dd>
            <Badge variant={branchStatusBadgeVariant(branch.status)}>{branchStatusLabel(branch.status)}</Badge>
          </dd>
        </div>
        <div className="detail-dl__row">
          <dt>Ubicación ficticia</dt>
          <dd>{branch.locationLabel}</dd>
        </div>
        <div className="detail-dl__row">
          <dt>Socios seed asignados</dt>
          <dd>{memberCount}</dd>
        </div>
        <div className="detail-dl__row">
          <dt>Descripción</dt>
          <dd>{branch.description}</dd>
        </div>
      </dl>
      <p className="detail-dl__note">
        Catálogo de demostración. No representa sucursales operativas ni permisos de acceso del backend.
      </p>
    </Modal>
  );
}
