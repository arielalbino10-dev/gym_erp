import { cloneElement, isValidElement } from "react";

export default function FormField({
  id,
  label,
  error,
  hint,
  required = false,
  children,
}) {
  const errorId = error ? `${id}-error` : undefined;
  const hintId = hint ? `${id}-hint` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  let control = children;
  if (isValidElement(children)) {
    control = cloneElement(children, {
      "aria-describedby": describedBy,
      "aria-invalid": error ? true : undefined,
    });
  }

  return (
    <div className="form-field">
      <label className="form-field__label" htmlFor={id}>
        {label}
        {required ? <span className="form-field__required"> (obligatorio)</span> : null}
      </label>
      {hint ? (
        <p id={hintId} className="form-field__hint">
          {hint}
        </p>
      ) : null}
      <div className="form-field__control">{control}</div>
      {error ? (
        <p id={errorId} className="form-field__error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
