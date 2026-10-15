export default function SelectInput({ id, value, onChange, options, ...rest }) {
  return (
    <select id={id} className="ui-select" value={value} onChange={onChange} {...rest}>
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
