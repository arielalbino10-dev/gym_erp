export default function EmptyState({ title, children }) {
  return (
    <div className="empty-state" role="status">
      {title ? <p className="empty-state__title">{title}</p> : null}
      {children}
    </div>
  );
}
