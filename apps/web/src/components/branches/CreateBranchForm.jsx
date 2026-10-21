import { useState } from "react";
import Button from "../ui/Button.jsx";
import FormField from "../ui/FormField.jsx";
import TextInput from "../ui/TextInput.jsx";

export default function CreateBranchForm({ onSubmit, busy, error }) {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      return;
    }
    await onSubmit({
      name: trimmed,
      code: code.trim() || undefined,
    });
    setName("");
    setCode("");
  }

  return (
    <form className="branch-create-form" onSubmit={handleSubmit}>
      <FormField label="Nombre de sucursal" htmlFor="branch-create-name">
        <TextInput
          id="branch-create-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={200}
        />
      </FormField>
      <FormField label="Código (opcional)" htmlFor="branch-create-code">
        <TextInput
          id="branch-create-code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          maxLength={32}
        />
      </FormField>
      {error ? (
        <p className="auth-form__error" role="alert">
          {error}
        </p>
      ) : null}
      <Button type="submit" disabled={busy || !name.trim()}>
        {busy ? "Creando…" : "Crear sucursal"}
      </Button>
    </form>
  );
}
