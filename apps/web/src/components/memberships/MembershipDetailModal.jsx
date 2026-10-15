import { Link } from "react-router-dom";
import Modal from "../ui/Modal.jsx";
import Badge from "../ui/Badge.jsx";
import Button from "../ui/Button.jsx";
import { lifecycleBadgeVariant, lifecycleLabel } from "../../demo/memberships.demo.js";
import { formatDemoDate, membershipTypeLabel } from "../../utils/memberLabels.js";

function formatIllustrativePrice(mxn) {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    maximumFractionDigits: 0,
  }).format(mxn);
}

export default function MembershipDetailModal({ assignment, onClose }) {
  if (!assignment) {
    return null;
  }

  return (
    <Modal
      isOpen={Boolean(assignment)}
      title={`Membresía asignada — ${assignment.memberCode}`}
      onClose={onClose}
      footer={
        <>
          <Link to="/socios" className="ui-btn ui-btn--secondary">
            Ir a socios (demo)
          </Link>
          <Button type="button" variant="primary" onClick={onClose}>
            Cerrar
          </Button>
        </>
      }
    >
      <dl className="detail-dl">
        <div className="detail-dl__row">
          <dt>Socio ficticio</dt>
          <dd>{assignment.fullName}</dd>
        </div>
        <div className="detail-dl__row">
          <dt>Código</dt>
          <dd>
            <code>{assignment.memberCode}</code>
          </dd>
        </div>
        <div className="detail-dl__row">
          <dt>Plan (catálogo)</dt>
          <dd>
            {assignment.planName} ({assignment.planCode})
          </dd>
        </div>
        <div className="detail-dl__row">
          <dt>Tipo</dt>
          <dd>{membershipTypeLabel(assignment.membershipType)}</dd>
        </div>
        <div className="detail-dl__row">
          <dt>Estado visual</dt>
          <dd>
            <Badge variant={lifecycleBadgeVariant(assignment.lifecycle)}>
              {lifecycleLabel(assignment.lifecycle)}
            </Badge>
          </dd>
        </div>
        <div className="detail-dl__row">
          <dt>Inicio</dt>
          <dd>{formatDemoDate(assignment.startDate)}</dd>
        </div>
        <div className="detail-dl__row">
          <dt>Vencimiento</dt>
          <dd>{formatDemoDate(assignment.endDate)}</dd>
        </div>
        <div className="detail-dl__row">
          <dt>Sucursal demo</dt>
          <dd>{assignment.branchName}</dd>
        </div>
        <div className="detail-dl__row">
          <dt>Importe ilustrativo</dt>
          <dd>{formatIllustrativePrice(assignment.priceIllustrativeMxn)} (no operativo)</dd>
        </div>
      </dl>
      <p className="detail-dl__note">Esta asignación es ficticia y no implica cobro, renovación ni contabilidad.</p>
    </Modal>
  );
}
