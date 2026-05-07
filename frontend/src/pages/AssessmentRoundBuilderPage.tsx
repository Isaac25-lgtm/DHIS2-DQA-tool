import { useSearchParams } from "react-router-dom";
import { AssessmentRoundEditor } from "../components/assessment/AssessmentRoundEditor";

export function AssessmentRoundBuilderPage() {
  const [searchParams] = useSearchParams();
  return <AssessmentRoundEditor initialTemplateRoundId={searchParams.get("template") ?? undefined} />;
}
