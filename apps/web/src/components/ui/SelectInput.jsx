export default function SelectInput({ id, value, onChange, options, className = "", ...rest }) {
  return (
    <select id={id} className={`ui-select ${className}`.trim()} value={value} onChange={onChange} {...rest}>
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
