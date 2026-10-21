import { useState } from "react";
import { useGymAuth } from "../app/providers/GymAuthProvider.jsx";
import Button from "../components/ui/Button.jsx";
import Card from "../components/ui/Card.jsx";
import FormField from "../components/ui/FormField.jsx";
import TextInput from "../components/ui/TextInput.jsx";

export default function LoginPage() {
  const { login, busy, error, setError } = useGymAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    try {
      await login({ email: email.trim(), password });
    } catch {
      /* error en contexto */
    }
  }

  return (
    <div className="auth-page">
      <Card title="Acceso gimnasio" className="auth-page__card">
        <p className="auth-page__hint">
          Inicie sesión con su cuenta de operación gym. Las credenciales no se almacenan en el
          navegador.
        </p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <FormField label="Correo" htmlFor="gym-login-email">
            <TextInput
              id="gym-login-email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </FormField>
          <FormField label="Contraseña" htmlFor="gym-login-password">
            <TextInput
              id="gym-login-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </FormField>
          {error ? (
            <p className="auth-form__error" role="alert">
              {error}
            </p>
          ) : null}
          <Button type="submit" disabled={busy}>
            {busy ? "Entrando…" : "Iniciar sesión"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
