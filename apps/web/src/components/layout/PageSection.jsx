export default function PageSection({ description, children }) {
  return (
    <>
      {description ? <p className="page-intro">{description}</p> : null}
      {children}
    </>
  );
}
