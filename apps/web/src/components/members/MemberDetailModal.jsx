import Modal from "../ui/Modal.jsx";
import Badge from "../ui/Badge.jsx";
import Button from "../ui/Button.jsx";
import {
  formatDemoDate,
  memberStatusBadgeVariant,
  memberStatusLabel,
  membershipTypeLabel,
} from "../../utils/memberLabels.js";

export default function MemberDetailModal({ member, onClose }) {
  if (!member) {
    return null;
  }

  return (
    <Modal
      isOpen={Boolean(member)}
      title={`Detalle — ${member.memberCode}`}
      onClose={onClose}
      footer={
        <Button type="button" variant="primary" onClick={onClose}>
          Cerrar
        </Button>
      }
    >
      <dl className="member-detail">
        <div className="member-detail__row">
          <dt>Nombre</dt>
          <dd>{member.fullName}</dd>
        </div>
        <div className="member-detail__row">
          <dt>Código demo</dt>
          <dd>
            <code>{member.memberCode}</code>
          </dd>
        </div>
        <div className="member-detail__row">
          <dt>Teléfono (ficticio)</dt>
          <dd>{member.phone}</dd>
        </div>
        <div className="member-detail__row">
          <dt>Membresía</dt>
          <dd>{membershipTypeLabel(member.membershipType)}</dd>
        </div>
        <div className="member-detail__row">
          <dt>Estado</dt>
          <dd>
            <Badge variant={memberStatusBadgeVariant(member.status)}>
              {memberStatusLabel(member.status)}
            </Badge>
          </dd>
        </div>
        <div className="member-detail__row">
          <dt>Inscripción</dt>
          <dd>{formatDemoDate(member.enrolledOn)}</dd>
        </div>
        <div className="member-detail__row">
          <dt>Vencimiento</dt>
          <dd>{formatDemoDate(member.expiresOn)}</dd>
        </div>
        <div className="member-detail__row">
          <dt>Sucursal demo</dt>
          <dd>{member.branchName}</dd>
        </div>
      </dl>
      {member.sessionOnly ? (
        <p className="member-detail__note" role="status">
          Registro agregado solo en esta sesión del navegador (demostración).
        </p>
      ) : null}
    </Modal>
  );
}
