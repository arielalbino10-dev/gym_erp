export default function TextInput({
  id,
  value,
  onChange,
  type = "text",
  placeholder,
  autoComplete = "off",
  ...rest
}) {
  return (
    <input
      id={id}
      className="ui-input"
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      autoComplete={autoComplete}
      {...rest}
    />
  );
}
