import Badge from "../ui/Badge.jsx";
import Button from "../ui/Button.jsx";
import Card from "../ui/Card.jsx";
import { branchStatusBadgeVariant, branchStatusLabel } from "../../demo/branches.demo.js";

export default function BranchesGrid({
  branches,
  memberCounts,
  onViewDetail,
  showMemberCounts = true,
}) {
  return (
    <div className="branches-grid">
      {branches.map((branch) => (
        <Card key={branch.branchId} title={branch.name} className="branches-grid__card">
          <p className="branches-grid__code">
            <Badge variant="demo">{branch.branchCode}</Badge>
            <Badge variant={branchStatusBadgeVariant(branch.status)}>{branchStatusLabel(branch.status)}</Badge>
          </p>
          <p className="branches-grid__location">{branch.locationLabel}</p>
          {showMemberCounts ? (
            <p className="branches-grid__meta">
              Socios ficticios asignados: <strong>{memberCounts[branch.branchId] ?? 0}</strong>
            </p>
          ) : null}
          {branch.description ? <p className="branches-grid__desc">{branch.description}</p> : null}
          {branch.timezone && !branch.description ? (
            <p className="branches-grid__desc">Zona horaria: {branch.timezone}</p>
          ) : null}
          <Button
            type="button"
            variant="secondary"
            onClick={() => onViewDetail(branch)}
            aria-label={`Ver detalle de sucursal ${branch.name}`}
          >
            Ver detalle
          </Button>
        </Card>
      ))}
    </div>
  );
}
