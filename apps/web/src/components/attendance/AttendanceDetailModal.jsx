import { Link } from "react-router-dom";
import Modal from "../ui/Modal.jsx";
import Button from "../ui/Button.jsx";
import { formatDemoDate } from "../../utils/memberLabels.js";

export default function AttendanceDetailModal({ record, onClose }) {
  if (!record) {
    return null;
  }

  return (
    <Modal
      isOpen={Boolean(record)}
      title={`Asistencia — ${record.recordId}`}
      onClose={onClose}
      footer={
        <>
          <Link to="/socios" className="ui-btn ui-btn--secondary">
            Ver socios (demo)
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
          <dd>{record.fullName}</dd>
        </div>
        <div className="detail-dl__row">
          <dt>Código</dt>
          <dd>
            <code>{record.memberCode}</code>
          </dd>
        </div>
        <div className="detail-dl__row">
          <dt>Fecha</dt>
          <dd>{formatDemoDate(record.dateIso)}</dd>
        </div>
        <div className="detail-dl__row">
          <dt>Hora (demo)</dt>
          <dd>{record.timeLocal}</dd>
        </div>
        <div className="detail-dl__row">
          <dt>Sucursal</dt>
          <dd>{record.branchName}</dd>
        </div>
        <div className="detail-dl__row">
          <dt>Registro</dt>
          <dd>{record.accessMethodLabel}</dd>
        </div>
      </dl>
      <p className="detail-dl__note">
        No se validó acceso real, torniquete ni membresía operativa. Solo visualización de datos ficticios.
      </p>
    </Modal>
  );
}
