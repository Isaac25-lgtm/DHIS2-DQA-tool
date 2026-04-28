import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowDown, ArrowUp, CheckCircle2, ClipboardList, MapPinned, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { z } from "zod";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { Textarea } from "../ui/Textarea";
import { useAuth } from "../../hooks/useAuth";
import { assessmentAssignmentService } from "../../services/assessmentAssignmentService";
import { assessmentRoundService } from "../../services/assessmentRoundService";
import { facilityService } from "../../services/facilityService";
import { indicatorService } from "../../services/indicatorService";
import { userService } from "../../services/userService";
import type {
  AssessmentRound,
  AssessmentRoundPayload,
  Facility,
  Indicator,
  PeriodType,
  SelectedIndicatorPayload,
  User,
  UserFormPayload,
} from "../../types";

const basicDetailsSchema = z.object({
  name: z.string().trim().min(1, "Assessment name is required."),
  reporting_period: z.string().trim().min(1, "Reporting period is required."),
  period_type: z.enum(["MONTHLY", "QUARTERLY", "ANNUAL", "CUSTOM"]),
  start_date: z.preprocess(
    (value) => value ?? "",
    z.string().trim().min(1, "Reporting period start date is required."),
  ),
  end_date: z.preprocess(
    (value) => value ?? "",
    z.string().trim().min(1, "Reporting period end date is required."),
  ),
  deadline: z.string().nullable(),
}).refine((value) => value.end_date >= value.start_date, {
  message: "Reporting period end date cannot be earlier than the start date.",
  path: ["end_date"],
});

const stepTitles = [
  "Basic details",
  "Select indicators",
  "Select facilities",
  "Assign field team",
  "Review and publish",
] as const;

const periodTypeOptions: PeriodType[] = ["MONTHLY", "QUARTERLY", "ANNUAL", "CUSTOM"];

const emptyForm: AssessmentRoundPayload = {
  name: "",
  description: "",
  reporting_period: "",
  period_type: "MONTHLY",
  start_date: null,
  end_date: null,
  deadline: null,
  notes: "",
};

const emptyAssessorForm: UserFormPayload = {
  full_name: "",
  email: "",
  password: "",
  role: "ASSESSOR",
  is_active: true,
};

interface AssessmentRoundEditorProps {
  roundId?: string;
}

export function AssessmentRoundEditor({ roundId }: AssessmentRoundEditorProps) {
  const { user } = useAuth();
  const isManager = user?.role === "MANAGER";

  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [round, setRound] = useState<AssessmentRound | null>(null);
  const [form, setForm] = useState<AssessmentRoundPayload>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [availableIndicators, setAvailableIndicators] = useState<Indicator[]>([]);
  const [availableFacilities, setAvailableFacilities] = useState<Facility[]>([]);
  const [assessors, setAssessors] = useState<User[]>([]);
  const [assessorForm, setAssessorForm] = useState<UserFormPayload>(emptyAssessorForm);
  const [creatingAssessor, setCreatingAssessor] = useState(false);

  const [indicatorSearch, setIndicatorSearch] = useState("");
  const [indicatorGroupFilter, setIndicatorGroupFilter] = useState("ALL");
  const [indicatorSectionFilter, setIndicatorSectionFilter] = useState("ALL");
  const [selectedIndicators, setSelectedIndicators] = useState<SelectedIndicatorPayload[]>([]);

  const [facilitySearch, setFacilitySearch] = useState("");
  const [selectedFacilityIds, setSelectedFacilityIds] = useState<string[]>([]);
  const [teamAssignments, setTeamAssignments] = useState<Record<string, { leadId: string; memberIds: string[] }>>({});
  const [allowUnassignedPublish, setAllowUnassignedPublish] = useState(false);

  const canEditDraft = isManager && (!round || round.status === "DRAFT");
  const canEditTeams =
    isManager && Boolean(round) && round?.status !== "CLOSED" && round?.status !== "ARCHIVED";

  const loadSupportData = async () => {
    const [indicators, facilities, users] = await Promise.all([
      indicatorService.listIndicators({ active: true }),
      facilityService.listFacilities({ active: true }),
      userService.listUsers().catch(() => []),
    ]);
    setAvailableIndicators(indicators.filter((item) => Boolean(item.dhis2_uid_or_operand?.trim())));
    setAvailableFacilities(facilities.filter((item) => Boolean(item.dhis2_org_unit_uid?.trim())));
    setAssessors(users.filter((item) => item.role === "ASSESSOR" && item.is_active));
  };

  const hydrateFromRound = (nextRound: AssessmentRound) => {
    setRound(nextRound);
    setForm({
      name: nextRound.name,
      description: nextRound.description,
      reporting_period: nextRound.reporting_period,
      period_type: nextRound.period_type,
      start_date: nextRound.start_date,
      end_date: nextRound.end_date,
      deadline: nextRound.deadline,
      notes: nextRound.notes,
      source_document_requirements: nextRound.source_document_requirements.map((item) => ({
        name: item.name,
        description: item.description,
        is_required: item.is_required,
        display_order: item.display_order,
      })),
    });
    setSelectedIndicators(
      nextRound.selected_indicators
        .filter((item) => Boolean(item.dhis2_uid_or_operand?.trim()))
        .map((item) => ({
          indicator_id: item.indicator_id,
          display_order: item.display_order,
          is_required: item.is_required,
          custom_threshold_percent: item.custom_threshold_percent,
          notes: item.notes,
        })),
    );
    setSelectedFacilityIds(
      nextRound.selected_facilities
        .filter((item) => Boolean(item.facility.dhis2_org_unit_uid?.trim()))
        .map((item) => item.facility_id),
    );
    setTeamAssignments(
      nextRound.selected_facilities.reduce<Record<string, { leadId: string; memberIds: string[] }>>((accumulator, item) => {
        const lead =
          item.team_members.find((member) => member.team_role === "TEAM_LEAD" && member.is_active)?.user_id ??
          item.assigned_assessor_id ??
          "";
        const memberIds = item.team_members
          .filter((member) => member.team_role === "TEAM_MEMBER" && member.is_active)
          .map((member) => member.user_id);
        accumulator[item.facility_id] = { leadId: lead, memberIds };
        return accumulator;
      }, {}),
    );
  };

  const loadRound = async (targetRoundId: string) => {
    const data = await assessmentRoundService.getRound(targetRoundId);
    hydrateFromRound(data);
  };

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        await loadSupportData();
        if (roundId) {
          await loadRound(roundId);
        }
      } catch {
        setFormError("Unable to load the assessment round builder right now.");
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [roundId]);

  const indicatorGroups = useMemo(
    () => ["ALL", ...Array.from(new Set(availableIndicators.map((item) => item.indicator_group))).sort()],
    [availableIndicators],
  );

  const indicatorSections = useMemo(
    () => [
      "ALL",
      ...Array.from(new Set(availableIndicators.map((item) => item.hmis_section).filter(Boolean) as string[])).sort(),
    ],
    [availableIndicators],
  );

  const filteredIndicators = useMemo(() => {
    const searchText = indicatorSearch.trim().toLowerCase();
    if (searchText.length < 2) {
      return [];
    }
    return availableIndicators.filter((item) => {
      const matchesSearch = [item.indicator_name, item.hmis_code, item.dhis2_uid_or_operand ?? "", item.source_register ?? ""]
        .join(" ")
        .toLowerCase()
        .includes(searchText);
      const matchesGroup = indicatorGroupFilter === "ALL" || item.indicator_group === indicatorGroupFilter;
      const matchesSection = indicatorSectionFilter === "ALL" || item.hmis_section === indicatorSectionFilter;
      return matchesSearch && matchesGroup && matchesSection;
    });
  }, [availableIndicators, indicatorSearch, indicatorGroupFilter, indicatorSectionFilter]);

  const filteredFacilities = useMemo(() => {
    return availableFacilities.filter((item) =>
      [item.facility_name, item.district, item.facility_type, item.ownership, item.dhis2_org_unit_uid ?? ""]
        .join(" ")
        .toLowerCase()
        .includes(facilitySearch.trim().toLowerCase()),
    );
  }, [availableFacilities, facilitySearch]);

  const selectedIndicatorDetails = useMemo(() => {
    return selectedIndicators
      .map((selection, index) => {
        const indicator = availableIndicators.find((item) => item.id === selection.indicator_id);
        return indicator ? { indicator, selection, index } : null;
      })
      .filter(Boolean) as { indicator: Indicator; selection: SelectedIndicatorPayload; index: number }[];
  }, [availableIndicators, selectedIndicators]);

  const selectedFacilityDetails = useMemo(() => {
    return selectedFacilityIds
      .map((facilityId) => availableFacilities.find((item) => item.id === facilityId))
      .filter(Boolean) as Facility[];
  }, [availableFacilities, selectedFacilityIds]);

  const toggleIndicator = (indicatorId: string) => {
    setSelectedIndicators((current) => {
      const exists = current.find((item) => item.indicator_id === indicatorId);
      if (exists) {
        return current
          .filter((item) => item.indicator_id !== indicatorId)
          .map((item, index) => ({ ...item, display_order: index + 1 }));
      }

      return [
        ...current,
        {
          indicator_id: indicatorId,
          display_order: current.length + 1,
          is_required: true,
          custom_threshold_percent: null,
          notes: null,
        },
      ];
    });
  };

  const moveIndicator = (index: number, direction: -1 | 1) => {
    setSelectedIndicators((current) => {
      const nextIndex = index + direction;
      if (nextIndex < 0 || nextIndex >= current.length) {
        return current;
      }

      const copy = [...current];
      const [item] = copy.splice(index, 1);
      copy.splice(nextIndex, 0, item);
      return copy.map((value, order) => ({ ...value, display_order: order + 1 }));
    });
  };

  const updateIndicatorSelection = (indicatorId: string, updates: Partial<SelectedIndicatorPayload>) => {
    setSelectedIndicators((current) =>
      current.map((item) => (item.indicator_id === indicatorId ? { ...item, ...updates } : item)),
    );
  };

  const toggleFacility = (facilityId: string) => {
    setSelectedFacilityIds((current) =>
      current.includes(facilityId) ? current.filter((item) => item !== facilityId) : [...current, facilityId],
    );
  };

  const createAssessorInline = async () => {
    setCreatingAssessor(true);
    setFormError(null);
    setMessage(null);
    try {
      if (!assessorForm.full_name.trim() || !assessorForm.email.trim() || !assessorForm.password?.trim()) {
        setFormError("Enter full name, email, and password before adding a team member.");
        return;
      }
      if ((assessorForm.password ?? "").length < 8) {
        setFormError("Team member password must be at least 8 characters.");
        return;
      }
      const created = await userService.createUser({
        ...assessorForm,
        full_name: assessorForm.full_name.trim(),
        email: assessorForm.email.trim(),
        password: assessorForm.password,
        role: "ASSESSOR",
        is_active: true,
      });
      setAssessors((current) =>
        [...current.filter((item) => item.id !== created.id), created].sort((left, right) =>
          left.full_name.localeCompare(right.full_name),
        ),
      );
      setAssessorForm(emptyAssessorForm);
      setMessage("Team member account created. You can now select them as Team Lead or Team Member.");
    } catch {
      setFormError("Unable to create this team member. Check whether the email already exists.");
    } finally {
      setCreatingAssessor(false);
    }
  };

  const saveBasicDetails = async () => {
    setSaving(true);
    setFormError(null);
    setMessage(null);
    try {
      basicDetailsSchema.parse({
        name: form.name,
        reporting_period: form.reporting_period,
        period_type: form.period_type,
        start_date: form.start_date,
        end_date: form.end_date,
        deadline: form.deadline,
      });

      const payload: AssessmentRoundPayload = {
        ...form,
        description: form.description || null,
        notes: form.notes || null,
      };

      const nextRound = round
        ? await assessmentRoundService.updateRound(round.id, payload)
        : await assessmentRoundService.createRound(payload);
      hydrateFromRound(nextRound);
      setActiveStep(1);
      setMessage(round ? "Assessment round updated." : "Draft assessment round created.");
    } catch (error) {
      if (error instanceof z.ZodError) {
        setFormError(error.issues[0]?.message ?? "Please review the basic details.");
      } else {
        setFormError("Unable to save round details right now.");
      }
    } finally {
      setSaving(false);
    }
  };

  const saveIndicators = async () => {
    if (!round) {
      setFormError("Create the draft round first.");
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      await assessmentRoundService.replaceIndicators(round.id, selectedIndicators);
      await loadRound(round.id);
      setActiveStep(2);
      setMessage("Selected indicators saved.");
    } catch {
      setFormError("Unable to save selected indicators.");
    } finally {
      setSaving(false);
    }
  };

  const saveFacilities = async () => {
    if (!round) {
      setFormError("Create the draft round first.");
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      await assessmentRoundService.replaceFacilities(round.id, { facility_ids: selectedFacilityIds });
      await loadRound(round.id);
      setActiveStep(3);
      setMessage("Selected facilities saved.");
    } catch {
      setFormError("Unable to save selected facilities.");
    } finally {
      setSaving(false);
    }
  };

  const saveAssignments = async () => {
    if (!round) {
      setFormError("Create the draft round first.");
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      const refreshedRound = await assessmentRoundService.getRound(round.id);
      const facilitiesByFacilityId = new Map(refreshedRound.selected_facilities.map((item) => [item.facility_id, item]));
      await Promise.all(
        selectedFacilityIds.map((facilityId) => {
          const assessmentFacility = facilitiesByFacilityId.get(facilityId);
          const team = teamAssignments[facilityId];
          if (!assessmentFacility || !team?.leadId) {
            return Promise.resolve();
          }
          const uniqueMembers = Array.from(new Set(team.memberIds.filter((memberId) => memberId !== team.leadId)));
          return assessmentAssignmentService.saveTeamMembers(assessmentFacility.id, {
            team_members: [
              {
                user_id: team.leadId,
                team_role: "TEAM_LEAD",
                can_enter_data: true,
                can_submit: true,
              },
              ...uniqueMembers.map((memberId) => ({
                user_id: memberId,
                team_role: "TEAM_MEMBER" as const,
                can_enter_data: true,
                can_submit: false,
              })),
            ],
          });
        }),
      );
      await loadRound(round.id);
      setActiveStep(4);
      setMessage("Field team assignments saved.");
    } catch {
      setFormError("Unable to save field team assignments.");
    } finally {
      setSaving(false);
    }
  };

  const publishRound = async () => {
    if (!round) {
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      const published = await assessmentRoundService.publishRound(round.id, {
        allow_unassigned_facilities: allowUnassignedPublish,
      });
      hydrateFromRound(published);
      setMessage("Assessment round published successfully.");
    } catch {
      setFormError("Unable to publish the assessment round. Confirm indicators, facilities, and assignments first.");
    } finally {
      setSaving(false);
    }
  };

  const closeRound = async () => {
    if (!round) {
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      const closed = await assessmentRoundService.closeRound(round.id);
      hydrateFromRound(closed);
      setMessage("Assessment round closed.");
    } catch {
      setFormError("Unable to close the assessment round right now.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card title="Assessment Round Builder" subtitle="Loading the manager planning workspace.">
        <div className="rounded-2xl border border-brand-border bg-brand-surface p-6 text-sm text-brand-muted">
          Loading round configuration...
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card
        title={round ? round.name : "New assessment round"}
        subtitle="Managers control round details, selected indicators, facility scope, and assessor assignments."
      >
        <div className="flex flex-wrap items-center gap-3">
          <Badge tone="info">{round ? round.status : "DRAFT"}</Badge>
          <Badge tone="neutral">{round ? round.reporting_period : "Not saved yet"}</Badge>
          {round?.start_date && round?.end_date ? (
            <Badge tone="info">
              {round.start_date} to {round.end_date}
            </Badge>
          ) : null}
          <Badge tone="success">{selectedIndicators.length} indicators selected</Badge>
          <Badge tone="warning">{selectedFacilityIds.length} facilities selected</Badge>
          {message ? <span className="text-sm font-medium text-brand-teal">{message}</span> : null}
        </div>
        {formError ? <p className="mt-4 text-sm text-brand-danger">{formError}</p> : null}
      </Card>

      <div className="grid gap-3 lg:grid-cols-5">
        {stepTitles.map((title, index) => {
          const isActive = index === activeStep;
          return (
            <button
              key={title}
              type="button"
              className={`rounded-2xl border px-4 py-3 text-left transition ${
                isActive
                  ? "border-brand-teal bg-cyan-50 text-brand-navy shadow-soft"
                  : "border-brand-border bg-white text-brand-muted"
              }`}
              onClick={() => setActiveStep(index)}
              disabled={index > 0 && !round}
            >
              <p className="text-xs uppercase tracking-[0.18em]">{`Step ${index + 1}`}</p>
              <p className="mt-2 text-sm font-semibold">{title}</p>
            </button>
          );
        })}
      </div>

      {activeStep === 0 ? (
        <Card title="Step 1: Basic details" subtitle="Create the draft round and define the reporting period with clear start and end dates.">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-semibold text-brand-text">Assessment name</label>
              <Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-brand-text">Period type</label>
              <Select
                value={form.period_type}
                onChange={(event) => setForm({ ...form, period_type: event.target.value as PeriodType })}
              >
                {periodTypeOptions.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </Select>
            </div>
            <div className="rounded-2xl border border-brand-border bg-brand-surface p-4 md:col-span-2">
              <p className="text-sm font-semibold text-brand-text">Reporting period</p>
              <p className="mt-1 text-xs text-brand-muted">
                The period label is used for DHIS2 pulls; the start and end dates define the assessment reporting window.
              </p>
              <div className="mt-4 grid gap-4 md:grid-cols-3">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-brand-text">Period label</label>
                  <Input
                    placeholder="Example: 2026-03"
                    value={form.reporting_period}
                    onChange={(event) => setForm({ ...form, reporting_period: event.target.value })}
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-brand-text">Start date</label>
                  <Input
                    type="date"
                    value={form.start_date ?? ""}
                    onChange={(event) => setForm({ ...form, start_date: event.target.value || null })}
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-brand-text">End date</label>
                  <Input
                    type="date"
                    value={form.end_date ?? ""}
                    onChange={(event) => setForm({ ...form, end_date: event.target.value || null })}
                  />
                </div>
              </div>
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-brand-text">Deadline</label>
              <Input
                type="date"
                value={form.deadline ?? ""}
                onChange={(event) => setForm({ ...form, deadline: event.target.value || null })}
              />
            </div>
            <div className="md:col-span-2">
              <label className="mb-2 block text-sm font-semibold text-brand-text">Description</label>
              <Textarea
                rows={4}
                value={form.description ?? ""}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
              />
            </div>
            <div className="md:col-span-2">
              <label className="mb-2 block text-sm font-semibold text-brand-text">Manager notes</label>
              <Textarea
                rows={3}
                value={form.notes ?? ""}
                onChange={(event) => setForm({ ...form, notes: event.target.value })}
              />
            </div>
          </div>
          <div className="mt-5 flex gap-2">
            <Button onClick={() => void saveBasicDetails()} disabled={!canEditDraft || saving}>
              {saving ? "Saving..." : round ? "Update draft details" : "Create draft round"}
            </Button>
            {round ? (
              <Button variant="secondary" onClick={() => setActiveStep(1)}>
                Continue to indicators
              </Button>
            ) : null}
          </div>
        </Card>
      ) : null}

      {activeStep === 1 ? (
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Card title="Step 2: Select indicators" subtitle="Search for imported DHIS2 HMIS 105 data elements, then add only the indicators needed for this assessment project.">
            <div className="grid gap-3 md:grid-cols-3">
              <Input placeholder="Search by HMIS code, data element name, or DHIS2 UID" value={indicatorSearch} onChange={(event) => setIndicatorSearch(event.target.value)} />
              <Select value={indicatorGroupFilter} onChange={(event) => setIndicatorGroupFilter(event.target.value)}>
                {indicatorGroups.map((group) => (
                  <option key={group} value={group}>
                    {group === "ALL" ? "All groups" : group}
                  </option>
                ))}
              </Select>
              <Select value={indicatorSectionFilter} onChange={(event) => setIndicatorSectionFilter(event.target.value)}>
                {indicatorSections.map((section) => (
                  <option key={section} value={section}>
                    {section === "ALL" ? "All sections" : section}
                  </option>
                ))}
              </Select>
            </div>

            <div className="mt-4 space-y-3">
              {indicatorSearch.trim().length < 2 ? (
                <div className="rounded-2xl border border-dashed border-brand-border bg-brand-surface p-5 text-sm text-brand-muted">
                  Start typing at least 2 characters to search imported DHIS2-backed HMIS 105 data elements. The full indicator library is hidden here to keep assessment setup focused.
                </div>
              ) : filteredIndicators.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-brand-border bg-brand-surface p-5 text-sm text-brand-muted">
                  No DHIS2-backed data elements match this search. Import HMIS 105 data elements from DHIS2 first.
                  <div className="mt-3">
                    <Link to="/indicators" className="font-semibold text-brand-teal">
                      Search DHIS2 data elements
                    </Link>
                  </div>
                </div>
              ) : filteredIndicators.map((indicator) => {
                const isSelected = selectedIndicators.some((item) => item.indicator_id === indicator.id);
                return (
                  <label key={indicator.id} className="flex gap-3 rounded-2xl border border-brand-border bg-white p-4">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleIndicator(indicator.id)}
                      className="mt-1 h-4 w-4"
                      disabled={!canEditDraft}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-brand-text">{indicator.indicator_name}</p>
                        <Badge tone="info">{indicator.hmis_code}</Badge>
                        <Badge tone="success">DHIS2 mapped</Badge>
                      </div>
                      <p className="mt-2 text-sm text-brand-muted">
                        {indicator.indicator_group}
                        {indicator.hmis_section ? ` - ${indicator.hmis_section}` : ""}
                        {indicator.source_register ? ` - ${indicator.source_register}` : ""}
                      </p>
                      <p className="mt-1 break-all text-xs text-brand-muted">
                        {indicator.dhis2_uid_or_operand}
                      </p>
                    </div>
                  </label>
                );
              })}
            </div>
            <div className="mt-5 flex gap-2">
              <Button onClick={() => void saveIndicators()} disabled={!canEditDraft || saving || !round}>
                {saving ? "Saving..." : "Save selected indicators"}
              </Button>
              <Button variant="secondary" onClick={() => setActiveStep(2)} disabled={!round}>
                Continue
              </Button>
            </div>
          </Card>

          <Card title="Selected indicators" subtitle={`${selectedIndicators.length} indicators currently scoped to this round.`}>
            {selectedIndicatorDetails.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-brand-border bg-brand-surface p-5 text-sm text-brand-muted">
                Select at least one indicator from the left before the round can be published.
              </div>
            ) : (
              <div className="space-y-3">
                {selectedIndicatorDetails.map(({ indicator, selection, index }) => (
                  <div key={indicator.id} className="rounded-2xl border border-brand-border bg-white p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-brand-text">{indicator.indicator_name}</p>
                        <p className="mt-1 text-sm text-brand-muted">{indicator.hmis_code} - order {selection.display_order}</p>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="secondary" className="px-3 py-2" onClick={() => moveIndicator(index, -1)} disabled={!canEditDraft}>
                          <ArrowUp size={16} />
                        </Button>
                        <Button variant="secondary" className="px-3 py-2" onClick={() => moveIndicator(index, 1)} disabled={!canEditDraft}>
                          <ArrowDown size={16} />
                        </Button>
                      </div>
                    </div>
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      <label className="flex items-center gap-2 text-sm text-brand-text">
                        <input
                          type="checkbox"
                          checked={selection.is_required}
                          onChange={(event) => updateIndicatorSelection(indicator.id, { is_required: event.target.checked })}
                          disabled={!canEditDraft}
                        />
                        Required for assessors
                      </label>
                      <Input
                        type="number"
                        placeholder="Custom threshold percent"
                        value={selection.custom_threshold_percent ?? ""}
                        onChange={(event) =>
                          updateIndicatorSelection(indicator.id, {
                            custom_threshold_percent: event.target.value ? Number(event.target.value) : null,
                          })
                        }
                        disabled={!canEditDraft}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      ) : null}

      {activeStep === 2 ? (
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Card title="Step 3: Select facilities" subtitle="Select only facilities imported from DHIS2 or linked to a DHIS2 org unit UID.">
            <Input
              placeholder="Search by facility, district, type, or DHIS2 UID"
              value={facilitySearch}
              onChange={(event) => setFacilitySearch(event.target.value)}
            />
            {availableFacilities.length === 0 ? (
              <div className="mt-4 rounded-2xl border border-dashed border-brand-border bg-brand-surface p-5 text-sm text-brand-muted">
                No DHIS2-linked facilities are available yet.
                <div className="mt-3">
                  <Link to="/facilities" className="font-semibold text-brand-teal">
                    Search DHIS2 facilities
                  </Link>
                </div>
              </div>
            ) : filteredFacilities.length === 0 ? (
              <div className="mt-4 rounded-2xl border border-dashed border-brand-border bg-brand-surface p-5 text-sm text-brand-muted">
                No imported DHIS2 facilities match this search.
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                {filteredFacilities.map((facility) => (
                  <label key={facility.id} className="flex gap-3 rounded-2xl border border-brand-border bg-white p-4">
                    <input
                      type="checkbox"
                      checked={selectedFacilityIds.includes(facility.id)}
                      onChange={() => toggleFacility(facility.id)}
                      className="mt-1 h-4 w-4"
                      disabled={!canEditDraft}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-brand-text">{facility.facility_name}</p>
                        <Badge tone="info">{facility.district}</Badge>
                        <Badge tone="neutral">{facility.facility_type}</Badge>
                        <Badge tone="success">DHIS2 linked</Badge>
                      </div>
                      <p className="mt-1 text-sm text-brand-muted">{facility.ownership}</p>
                      <p className="mt-1 break-all text-xs text-brand-muted">
                        DHIS2 org unit UID: {facility.dhis2_org_unit_uid ?? "Missing from local registry"}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            )}
            <div className="mt-5 flex gap-2">
              <Button onClick={() => void saveFacilities()} disabled={!canEditDraft || saving || !round}>
                {saving ? "Saving..." : "Save selected facilities"}
              </Button>
            </div>
          </Card>

          <Card title="Selected facilities" subtitle={`${selectedFacilityIds.length} facilities currently included in the round.`}>
            {selectedFacilityDetails.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-brand-border bg-brand-surface p-5 text-sm text-brand-muted">
                Add facilities from the local registry before you move to assessor assignment.
              </div>
            ) : (
              <div className="space-y-3">
                {selectedFacilityDetails.map((facility) => (
                  <div key={facility.id} className="rounded-2xl border border-brand-border bg-white p-4">
                    <p className="font-semibold text-brand-text">{facility.facility_name}</p>
                    <p className="mt-1 text-sm text-brand-muted">{facility.district} - {facility.facility_type}</p>
                    <p className="mt-1 break-all text-xs text-brand-muted">{facility.dhis2_org_unit_uid ?? "Missing DHIS2 UID"}</p>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      ) : null}

      {activeStep === 3 ? (
        <div className="space-y-6">
          <Card title="Add assessment team member" subtitle="Create assessor accounts here, then choose one as Team Lead and optional Team Members below.">
            <div className="grid gap-4 lg:grid-cols-[1fr_1fr_1fr_auto] lg:items-end">
              <div>
                <label className="mb-2 block text-sm font-semibold text-brand-text">Full name</label>
                <Input
                  value={assessorForm.full_name}
                  onChange={(event) => setAssessorForm({ ...assessorForm, full_name: event.target.value })}
                  placeholder="Team member name"
                  disabled={!canEditTeams}
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-semibold text-brand-text">Email</label>
                <Input
                  type="email"
                  value={assessorForm.email}
                  onChange={(event) => setAssessorForm({ ...assessorForm, email: event.target.value })}
                  placeholder="name@example.org"
                  disabled={!canEditTeams}
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-semibold text-brand-text">Temporary password</label>
                <Input
                  type="password"
                  value={assessorForm.password ?? ""}
                  onChange={(event) => setAssessorForm({ ...assessorForm, password: event.target.value })}
                  placeholder="Minimum 8 characters"
                  disabled={!canEditTeams}
                />
              </div>
              <Button onClick={() => void createAssessorInline()} disabled={!canEditTeams || creatingAssessor}>
                {creatingAssessor ? "Adding..." : "Add member"}
              </Button>
            </div>
          </Card>

          <Card title="Step 4: Assign field team" subtitle="Each selected facility needs a Team Lead. Managers can change teams until the facility assessment is submitted or closed.">
          {selectedFacilityDetails.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-brand-border bg-brand-surface p-5 text-sm text-brand-muted">
              No facilities selected yet. Go back one step and add facilities first.
            </div>
          ) : assessors.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-brand-border bg-brand-surface p-5 text-sm text-brand-muted">
              No active assessor users exist yet. Add at least one team member above.
            </div>
          ) : (
            <div className="space-y-4">
              {selectedFacilityDetails.map((facility) => (
                <div key={facility.id} className="grid gap-3 rounded-2xl border border-brand-border bg-white p-4 lg:grid-cols-[1fr_260px] lg:items-center">
                  <div>
                    <p className="font-semibold text-brand-text">{facility.facility_name}</p>
                    <p className="mt-1 text-sm text-brand-muted">{facility.district} - {facility.facility_type}</p>
                    {!teamAssignments[facility.id]?.leadId ? (
                      <div className="mt-2 flex items-center gap-2 text-sm text-brand-warning">
                        <AlertTriangle size={14} />
                        Team Lead required
                      </div>
                    ) : null}
                  </div>
                  <div className="space-y-3">
                    <Select
                      value={teamAssignments[facility.id]?.leadId ?? ""}
                      onChange={(event) =>
                        setTeamAssignments((current) => ({
                          ...current,
                          [facility.id]: {
                            leadId: event.target.value,
                            memberIds: current[facility.id]?.memberIds ?? [],
                          },
                        }))
                      }
                      disabled={!canEditTeams}
                    >
                      <option value="">Select Team Lead</option>
                      {assessors.map((assessor) => (
                        <option key={assessor.id} value={assessor.id}>
                          {assessor.full_name}
                        </option>
                      ))}
                    </Select>
                    <div className="rounded-xl bg-brand-surface p-3">
                      <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-brand-muted">
                        Team Members
                      </p>
                      <div className="grid gap-2">
                        {assessors.map((assessor) => {
                          const currentTeam = teamAssignments[facility.id] ?? { leadId: "", memberIds: [] };
                          const checked = currentTeam.memberIds.includes(assessor.id);
                          return (
                            <label key={assessor.id} className="flex items-center gap-2 text-sm text-brand-text">
                              <input
                                type="checkbox"
                                checked={checked}
                                disabled={!canEditTeams || currentTeam.leadId === assessor.id}
                                onChange={(event) =>
                                  setTeamAssignments((current) => {
                                    const existing = current[facility.id] ?? { leadId: "", memberIds: [] };
                                    const memberIds = event.target.checked
                                      ? Array.from(new Set([...existing.memberIds, assessor.id]))
                                      : existing.memberIds.filter((memberId) => memberId !== assessor.id);
                                    return { ...current, [facility.id]: { ...existing, memberIds } };
                                  })
                                }
                              />
                              {assessor.full_name}
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="mt-5 flex gap-2">
            <Button onClick={() => void saveAssignments()} disabled={!canEditTeams || saving || !round}>
              {saving ? "Saving..." : "Save assignments"}
            </Button>
            <Button variant="secondary" onClick={() => setActiveStep(4)} disabled={!round}>
              Continue to review
            </Button>
          </div>
          </Card>
        </div>
      ) : null}

      {activeStep === 4 ? (
        <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <Card title="Step 5: Review and publish" subtitle="Confirm the round scope before assessors can see it.">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl bg-brand-surface p-4">
                <div className="flex items-center gap-2 text-brand-muted">
                  <ClipboardList size={16} />
                  Indicators
                </div>
                <p className="mt-3 text-3xl font-bold text-brand-navy">{selectedIndicators.length}</p>
              </div>
              <div className="rounded-2xl bg-brand-surface p-4">
                <div className="flex items-center gap-2 text-brand-muted">
                  <MapPinned size={16} />
                  Facilities
                </div>
                <p className="mt-3 text-3xl font-bold text-brand-navy">{selectedFacilityIds.length}</p>
              </div>
              <div className="rounded-2xl bg-brand-surface p-4">
                <div className="flex items-center gap-2 text-brand-muted">
                  <Users size={16} />
                  Team Lead assigned
                </div>
                <p className="mt-3 text-3xl font-bold text-brand-navy">
                  {selectedFacilityIds.filter((facilityId) => Boolean(teamAssignments[facilityId]?.leadId)).length}
                </p>
              </div>
            </div>

            <div className="mt-5 rounded-2xl border border-brand-border bg-white p-4">
              <p className="text-sm font-semibold text-brand-text">Source document requirements</p>
              <div className="mt-3 space-y-2">
                {(round?.source_document_requirements ?? []).map((item) => (
                  <div key={item.id} className="flex items-center justify-between rounded-xl bg-brand-surface px-3 py-2">
                    <span className="text-sm text-brand-text">{item.name}</span>
                    <Badge tone={item.is_required ? "success" : "neutral"}>
                      {item.is_required ? "Required" : "Optional"}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 text-sm text-brand-text">
                <input
                  type="checkbox"
                  checked={allowUnassignedPublish}
                  onChange={(event) => setAllowUnassignedPublish(event.target.checked)}
                  disabled={!canEditDraft}
                />
                Allow publishing with Team Lead-only facility teams
              </label>
            </div>

            <div className="mt-5 flex flex-wrap gap-2">
              <Button onClick={() => void publishRound()} disabled={!canEditDraft || saving || !round}>
                {saving ? "Publishing..." : "Publish round"}
              </Button>
              {round ? (
                <Button variant="secondary" onClick={() => void closeRound()} disabled={!isManager || saving}>
                  Close round
                </Button>
              ) : null}
            </div>
          </Card>

          <Card title="Configuration summary" subtitle="This package becomes the future offline-ready assessment definition.">
            <div className="space-y-4">
              <div className="rounded-2xl bg-brand-navy p-5 text-white">
                <p className="text-sm text-slate-200">Assessment package readiness</p>
                <p className="mt-2 text-2xl font-bold">
                  {round?.status === "PUBLISHED" ? "Ready for assessors" : "Draft package in progress"}
                </p>
                <p className="mt-2 text-sm text-slate-200">
                  The selected indicators, facilities, assessor assignments, period, and document requirements will later be cached offline.
                </p>
              </div>
              <div className="rounded-2xl border border-brand-border bg-white p-4">
                <p className="text-sm font-semibold text-brand-text">Unassigned facilities</p>
                <p className="mt-2 text-brand-muted">
                  {selectedFacilityIds.filter((facilityId) => !teamAssignments[facilityId]?.leadId).length}
                </p>
              </div>
              <div className="rounded-2xl border border-brand-border bg-white p-4">
                <p className="text-sm font-semibold text-brand-text">Deadline</p>
                <p className="mt-2 text-brand-muted">{round?.deadline ?? "No deadline set"}</p>
              </div>
              <div className="rounded-2xl border border-brand-border bg-white p-4">
                <div className="flex items-center gap-2 text-brand-muted">
                  <CheckCircle2 size={16} />
                  Offline preparation
                </div>
                <p className="mt-2 text-sm text-brand-text">
                  This package becomes the field team workspace with selected facilities, selected data elements, DHIS2 values, and source document checks.
                </p>
              </div>
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
