import { useState } from "react";
import Modal from "../ui/Modal.jsx";
import Button from "../ui/Button.jsx";
import FormField from "../ui/FormField.jsx";
import SelectInput from "../ui/SelectInput.jsx";
import TextInput from "../ui/TextInput.jsx";
import { branchFilterOptionsForLists } from "../../demo/branches.demo.js";
import { MEMBERSHIP_TYPES, createSessionDemoMember } from "../../demo/members.demo.js";

const MEMBERSHIP_OPTIONS = [
  { value: MEMBERSHIP_TYPES.MONTHLY, label: "Mensual (demo)" },
  { value: MEMBERSHIP_TYPES.QUARTERLY, label: "Trimestral (demo)" },
  { value: MEMBERSHIP_TYPES.ANNUAL, label: "Anual (demo)" },
];

const BRANCH_OPTIONS = branchFilterOptionsForLists().filter((opt) => opt.value !== "");
const DEFAULT_BRANCH_ID = BRANCH_OPTIONS[0]?.value ?? "";

function validate(fields) {
  const errors = {};
  const name = fields.fullName.trim();
  if (!name) {
    errors.fullName = "Indique el nombre completo del socio ficticio.";
  } else if (name.length < 3) {
    errors.fullName = "Use al menos 3 caracteres (dato de demostración).";
  }
  const phone = fields.phone.trim();
  if (!phone) {
    errors.phone = "Indique un teléfono ficticio.";
  } else if (!/^[\d\s+\-()]{8,20}$/.test(phone)) {
    errors.phone = "Formato de teléfono demo no válido (solo dígitos y separadores).";
  }
  if (!fields.membershipType) {
    errors.membershipType = "Seleccione un tipo de membresía.";
  }
  if (!fields.branchId) {
    errors.branchId = "Seleccione una sucursal demo.";
  }
  return errors;
}

export default function NewMemberDemoModal({ isOpen, onClose, sessionIndex, onCreated }) {
  const [fields, setFields] = useState({
    fullName: "",
    phone: "",
    membershipType: MEMBERSHIP_TYPES.MONTHLY,
    branchId: DEFAULT_BRANCH_ID,
  });
  const [errors, setErrors] = useState({});

  function resetForm() {
    setFields({
      fullName: "",
      phone: "",
      membershipType: MEMBERSHIP_TYPES.MONTHLY,
      branchId: DEFAULT_BRANCH_ID,
    });
    setErrors({});
  }

  function isDirty() {
    return (
      fields.fullName.trim() !== "" ||
      fields.phone.trim() !== "" ||
      fields.membershipType !== MEMBERSHIP_TYPES.MONTHLY ||
      fields.branchId !== DEFAULT_BRANCH_ID
    );
  }

  function handleClose() {
    if (isDirty() && !window.confirm("¿Descartar los datos del formulario de demostración?")) {
      return;
    }
    resetForm();
    onClose();
  }

  function handleSubmit(event) {
    event.preventDefault();
    const nextErrors = validate(fields);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      const focusIds = {
        fullName: "demo-full-name",
        phone: "demo-phone",
        membershipType: "demo-membership",
        branchId: "demo-branch",
      };
      const firstKey = Object.keys(nextErrors)[0];
      document.getElementById(focusIds[firstKey])?.focus();
      return;
    }
    const member = createSessionDemoMember(fields, sessionIndex);
    onCreated(member);
    resetForm();
    onClose();
  }

  function patchField(key, value) {
    setFields((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <Modal
      isOpen={isOpen}
      title="Nuevo socio (Demo)"
      onClose={handleClose}
      closeOnBackdrop={false}
      footer={
        <>
          <Button type="button" variant="secondary" onClick={handleClose}>
            Cancelar
          </Button>
          <Button type="submit" form="new-member-demo-form" variant="primary">
            Guardar en memoria
          </Button>
        </>
      }
    >
      <p className="members-form__intro">
        Los datos no se envían al servidor ni se guardan al recargar la página.
      </p>
      <form id="new-member-demo-form" onSubmit={handleSubmit} noValidate>
        <FormField id="demo-full-name" label="Nombre completo" required error={errors.fullName}>
          <TextInput
            id="demo-full-name"
            data-modal-initial-focus=""
            value={fields.fullName}
            onChange={(e) => patchField("fullName", e.target.value)}
            placeholder="Ej. Socio ficticio demo"
          />
        </FormField>
        <FormField id="demo-phone" label="Teléfono ficticio" required error={errors.phone}>
          <TextInput
            id="demo-phone"
            type="tel"
            value={fields.phone}
            onChange={(e) => patchField("phone", e.target.value)}
            placeholder="55 8000 0000"
          />
        </FormField>
        <FormField id="demo-membership" label="Tipo de membresía" required error={errors.membershipType}>
          <SelectInput
            id="demo-membership"
            value={fields.membershipType}
            onChange={(e) => patchField("membershipType", e.target.value)}
            options={MEMBERSHIP_OPTIONS}
          />
        </FormField>
        <FormField id="demo-branch" label="Sucursal demo" required error={errors.branchId}>
          <SelectInput
            id="demo-branch"
            value={fields.branchId}
            onChange={(e) => patchField("branchId", e.target.value)}
            options={BRANCH_OPTIONS}
          />
        </FormField>
      </form>
    </Modal>
  );
}
