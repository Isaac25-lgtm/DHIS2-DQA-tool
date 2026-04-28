import { useParams } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { AssessmentRoundEditor } from "../components/assessment/AssessmentRoundEditor";

export function AssessmentRoundDetailPage() {
  const { id } = useParams();

  if (!id) {
    return (
      <Card title="Assessment round not found" subtitle="The requested assessment round identifier is missing.">
        <p className="text-sm text-brand-muted">Return to the assessment rounds list and reopen the round.</p>
      </Card>
    );
  }

  return <AssessmentRoundEditor roundId={id} />;
}
