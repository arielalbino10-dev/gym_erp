import Badge from "./Badge.jsx";

export default function PageHeader({ title, description, children }) {
  return (
    <header className="page-header-block">
      <div className="page-header-block__main">
        <div className="page-header-block__titles">
          <Badge variant="demo">Datos de demostración</Badge>
          <h2 className="page-header-block__title">{title}</h2>
          {description ? <p className="page-header-block__description">{description}</p> : null}
        </div>
        {children ? <div className="page-header-block__actions">{children}</div> : null}
      </div>
    </header>
  );
}
