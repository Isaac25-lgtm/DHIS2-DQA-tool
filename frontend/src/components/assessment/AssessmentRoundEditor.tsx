import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowDown, ArrowUp, CheckCircle2, ClipboardList, MapPinned, Users } from "lucide-react";
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
import { dhis2Service } from "../../services/dhis2Service";
import { facilityService } from "../../services/facilityService";
import { indicatorService } from "../../services/indicatorService";
import { userService } from "../../services/userService";
import type {
  AssessmentRound,
  AssessmentRoundPayload,
  Dhis2DataElementSearchResult,
  Dhis2FacilitySearchResult,
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
  "Create shared group logins",
  "Review and publish",
] as const;

const periodTypeOptions: PeriodType[] = ["MONTHLY", "QUARTERLY", "ANNUAL", "CUSTOM"];

function deriveReportingPeriod(periodType: PeriodType, startDate: string | null, endDate: string | null, fallback = "") {
  if (!startDate) {
    return fallback;
  }
  const [year, month] = startDate.split("-");
  if (!year || !month) {
    return fallback;
  }
  if (periodType === "MONTHLY") {
    return `${year}${month}`;
  }
  if (periodType === "QUARTERLY") {
    return `${year}Q${Math.ceil(Number(month) / 3)}`;
  }
  if (periodType === "ANNUAL") {
    return year;
  }
  const compactStartDate = startDate.replace(/-/g, "");
  if (endDate) {
    return `${compactStartDate}-${endDate.replace(/-/g, "")}`;
  }
  return compactStartDate;
}

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
  const [syncingDhis2, setSyncingDhis2] = useState(false);
  const [round, setRound] = useState<AssessmentRound | null>(null);
  const [form, setForm] = useState<AssessmentRoundPayload>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [availableIndicators, setAvailableIndicators] = useState<Indicator[]>([]);
  const [availableFacilities, setAvailableFacilities] = useState<Facility[]>([]);
  const [allAssessors, setAllAssessors] = useState<User[]>([]);
  const [managedSharedLoginIds, setManagedSharedLoginIds] = useState<string[]>([]);
  const [assessorForm, setAssessorForm] = useState<UserFormPayload>(emptyAssessorForm);
  const [editingAssessorId, setEditingAssessorId] = useState<string | null>(null);
  const [creatingAssessor, setCreatingAssessor] = useState(false);
  const [deletingAssessorId, setDeletingAssessorId] = useState<string | null>(null);
  const [sharedLoginPasswords, setSharedLoginPasswords] = useState<Record<string, string>>({});
  const [sharedLoginPasswordsReady, setSharedLoginPasswordsReady] = useState(false);

  const [indicatorSearch, setIndicatorSearch] = useState("");
  const [dhis2IndicatorResults, setDhis2IndicatorResults] = useState<Dhis2DataElementSearchResult[]>([]);
  const [searchingDhis2Indicators, setSearchingDhis2Indicators] = useState(false);
  const [importingIndicatorUid, setImportingIndicatorUid] = useState<string | null>(null);
  const [indicatorGroupFilter, setIndicatorGroupFilter] = useState("ALL");
  const [indicatorSectionFilter, setIndicatorSectionFilter] = useState("ALL");
  const [selectedIndicators, setSelectedIndicators] = useState<SelectedIndicatorPayload[]>([]);

  const [facilitySearch, setFacilitySearch] = useState("");
  const [dhis2FacilityResults, setDhis2FacilityResults] = useState<Dhis2FacilitySearchResult[]>([]);
  const [searchingDhis2Facilities, setSearchingDhis2Facilities] = useState(false);
  const [importingFacilityUid, setImportingFacilityUid] = useState<string | null>(null);
  const [selectedFacilityIds, setSelectedFacilityIds] = useState<string[]>([]);
  const [teamAssignments, setTeamAssignments] = useState<Record<string, { leadId: string; memberIds: string[] }>>({});
  const [allowUnassignedPublish, setAllowUnassignedPublish] = useState(false);

  const canEditDraft = isManager && (!round || round.status === "DRAFT");
  const canEditTeams =
    isManager && Boolean(round) && round?.status !== "CLOSED" && round?.status !== "ARCHIVED";
  const sharedLoginPasswordStorageKey = round?.id ? `assessment-round-shared-login-passwords:${round.id}` : null;

  const loadSupportData = async () => {
    const [indicators, facilities, users] = await Promise.all([
      indicatorService.listIndicators({ active: true }),
      facilityService.listFacilities({ active: true }),
      userService.listUsers().catch(() => []),
    ]);
    setAvailableIndicators(indicators.filter((item) => Boolean(item.dhis2_uid_or_operand?.trim())));
    setAvailableFacilities(facilities.filter((item) => Boolean(item.dhis2_org_unit_uid?.trim())));
    setAllAssessors(users.filter((item) => item.role === "ASSESSOR" && item.is_active));
  };

  const mergeManagedSharedLoginIds = (nextIds: string[]) => {
    setManagedSharedLoginIds((current) => Array.from(new Set([...current, ...nextIds])));
  };

  const removeManagedSharedLoginId = (userId: string) => {
    setManagedSharedLoginIds((current) => current.filter((id) => id !== userId));
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
    mergeManagedSharedLoginIds(
      nextRound.selected_facilities.flatMap((item) => {
        const sharedLoginIds = item.team_members
          .filter((member) => member.is_active)
          .map((member) => member.user_id);
        if (item.assigned_assessor_id) {
          sharedLoginIds.push(item.assigned_assessor_id);
        }
        return sharedLoginIds;
      }),
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

  useEffect(() => {
    if (!sharedLoginPasswordStorageKey) {
      setSharedLoginPasswords({});
      setSharedLoginPasswordsReady(false);
      return;
    }

    try {
      const storedPasswords = window.sessionStorage.getItem(sharedLoginPasswordStorageKey);
      if (!storedPasswords) {
        setSharedLoginPasswords({});
      } else {
        const parsedPasswords = JSON.parse(storedPasswords) as Record<string, string>;
        setSharedLoginPasswords(
          Object.fromEntries(
            Object.entries(parsedPasswords).filter(
              ([userId, password]) => typeof userId === "string" && typeof password === "string",
            ),
          ),
        );
      }
    } catch {
      setSharedLoginPasswords({});
    } finally {
      setSharedLoginPasswordsReady(true);
    }
  }, [sharedLoginPasswordStorageKey]);

  useEffect(() => {
    if (!sharedLoginPasswordStorageKey || !sharedLoginPasswordsReady) {
      return;
    }

    const activeAssessorIds = new Set(managedSharedLoginIds);
    const visiblePasswords = Object.fromEntries(
      Object.entries(sharedLoginPasswords).filter(([userId, password]) => activeAssessorIds.has(userId) && password.trim().length > 0),
    );

    if (Object.keys(visiblePasswords).length === 0) {
      window.sessionStorage.removeItem(sharedLoginPasswordStorageKey);
      return;
    }

    window.sessionStorage.setItem(sharedLoginPasswordStorageKey, JSON.stringify(visiblePasswords));
  }, [managedSharedLoginIds, sharedLoginPasswordStorageKey, sharedLoginPasswords, sharedLoginPasswordsReady]);

  useEffect(() => {
    const query = indicatorSearch.trim();
    if (activeStep !== 1 || query.length < 2 || !canEditDraft) {
      setDhis2IndicatorResults([]);
      return;
    }

    const timer = window.setTimeout(async () => {
      setSearchingDhis2Indicators(true);
      try {
        const results = await dhis2Service.searchDataElements(query);
        setDhis2IndicatorResults(results);
      } catch {
        setDhis2IndicatorResults([]);
      } finally {
        setSearchingDhis2Indicators(false);
      }
    }, 450);

    return () => window.clearTimeout(timer);
  }, [activeStep, canEditDraft, indicatorSearch]);

  useEffect(() => {
    const query = facilitySearch.trim();
    if (activeStep !== 2 || query.length < 2 || !canEditDraft) {
      setDhis2FacilityResults([]);
      return;
    }

    const timer = window.setTimeout(async () => {
      setSearchingDhis2Facilities(true);
      try {
        const results = await dhis2Service.searchFacilities(query);
        setDhis2FacilityResults(results);
      } catch {
        setDhis2FacilityResults([]);
      } finally {
        setSearchingDhis2Facilities(false);
      }
    }, 450);

    return () => window.clearTimeout(timer);
  }, [activeStep, canEditDraft, facilitySearch]);

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

  const assessors = useMemo(
    () =>
      allAssessors
        .filter((assessor) => managedSharedLoginIds.includes(assessor.id))
        .sort((left, right) => left.full_name.localeCompare(right.full_name)),
    [allAssessors, managedSharedLoginIds],
  );

  const sharedLoginsById = useMemo(
    () => new Map(assessors.map((assessor) => [assessor.id, assessor])),
    [assessors],
  );

  const sharedLoginUsageCounts = useMemo(
    () =>
      selectedFacilityIds.reduce<Record<string, number>>((accumulator, facilityId) => {
        const leadId = teamAssignments[facilityId]?.leadId;
        if (!leadId) {
          return accumulator;
        }
        accumulator[leadId] = (accumulator[leadId] ?? 0) + 1;
        return accumulator;
      }, {}),
    [selectedFacilityIds, teamAssignments],
  );

  const reviewFacilityAssignments = useMemo(
    () =>
      selectedFacilityDetails.map((facility) => ({
        facility,
        assignedLogin: sharedLoginsById.get(teamAssignments[facility.id]?.leadId ?? ""),
      })),
    [selectedFacilityDetails, sharedLoginsById, teamAssignments],
  );

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

  const importAndSelectIndicator = async (result: Dhis2DataElementSearchResult) => {
    setImportingIndicatorUid(result.dhis2_uid_or_operand);
    setFormError(null);
    try {
      const indicator = await indicatorService.importFromDhis2(result);
      setAvailableIndicators((current) =>
        [indicator, ...current.filter((item) => item.id !== indicator.id)].filter((item) =>
          Boolean(item.dhis2_uid_or_operand?.trim()),
        ),
      );
      setSelectedIndicators((current) => {
        if (current.some((item) => item.indicator_id === indicator.id)) {
          return current;
        }
        return [
          ...current,
          {
            indicator_id: indicator.id,
            display_order: current.length + 1,
            is_required: true,
            custom_threshold_percent: null,
            notes: null,
          },
        ];
      });
      setMessage(`${indicator.hmis_code} imported from DHIS2 and added to this assessment.`);
    } catch {
      setFormError("Unable to import this DHIS2 data element. Confirm your DHIS2 sign-in and try again.");
    } finally {
      setImportingIndicatorUid(null);
    }
  };

  const importAndSelectFacility = async (result: Dhis2FacilitySearchResult) => {
    setImportingFacilityUid(result.dhis2_org_unit_uid);
    setFormError(null);
    try {
      const facility = await facilityService.importFromDhis2(result);
      setAvailableFacilities((current) =>
        [facility, ...current.filter((item) => item.id !== facility.id)].filter((item) =>
          Boolean(item.dhis2_org_unit_uid?.trim()),
        ),
      );
      setSelectedFacilityIds((current) => (current.includes(facility.id) ? current : [...current, facility.id]));
      setTeamAssignments((current) => ({
        ...current,
        [facility.id]: current[facility.id] ?? { leadId: "", memberIds: [] },
      }));
      setMessage(`${facility.facility_name} imported from DHIS2 and added to this assessment.`);
    } catch {
      setFormError("Unable to import this DHIS2 facility. Confirm your DHIS2 sign-in and try again.");
    } finally {
      setImportingFacilityUid(null);
    }
  };

  const createAssessorInline = async () => {
    setCreatingAssessor(true);
    setFormError(null);
    setMessage(null);
    try {
      const hasPassword = Boolean(assessorForm.password?.trim());
      if (!assessorForm.full_name.trim() || !assessorForm.email.trim() || (!editingAssessorId && !hasPassword)) {
        setFormError("Enter a group name, shared login email, and shared password before creating the group login.");
        return;
      }
      if (hasPassword && (assessorForm.password ?? "").length < 8) {
        setFormError("Shared group password must be at least 8 characters.");
        return;
      }
      const payload: UserFormPayload = {
        full_name: assessorForm.full_name.trim(),
        email: assessorForm.email.trim(),
        password: hasPassword ? assessorForm.password : undefined,
        role: "ASSESSOR",
        is_active: true,
      };
      const created = editingAssessorId
        ? await userService.updateUser(editingAssessorId, payload)
        : await userService.createUser({
            ...payload,
            password: payload.password ?? "",
          });
      setAllAssessors((current) => [...current.filter((item) => item.id !== created.id), created]);
      mergeManagedSharedLoginIds([created.id]);
      if (payload.password) {
        setSharedLoginPasswords((current) => ({
          ...current,
          [created.id]: payload.password ?? "",
        }));
      }
      setAssessorForm(emptyAssessorForm);
      setEditingAssessorId(null);
      setMessage(
        editingAssessorId
          ? "Shared group login updated. The manager changes now apply to that group account."
          : "Shared group login created. Anyone who signs in with those exact credentials will open that group's assigned facilities in this assessment project.",
      );
    } catch {
      setFormError(
        editingAssessorId
          ? "Unable to update this shared group login. Check whether the email already exists."
          : "Unable to create this shared group login. Check whether the email already exists.",
      );
    } finally {
      setCreatingAssessor(false);
    }
  };

  const startEditingAssessor = (assessor: User) => {
    setEditingAssessorId(assessor.id);
    setAssessorForm({
      full_name: assessor.full_name,
      email: assessor.email,
      password: "",
      role: "ASSESSOR",
      is_active: assessor.is_active,
    });
    setFormError(null);
    setMessage(null);
  };

  const deleteAssessorInline = async (assessor: User) => {
    setDeletingAssessorId(assessor.id);
    setFormError(null);
    setMessage(null);
    try {
      await userService.deactivateUser(assessor.id);
      setAllAssessors((current) => current.filter((item) => item.id !== assessor.id));
      removeManagedSharedLoginId(assessor.id);
      if (editingAssessorId === assessor.id) {
        setEditingAssessorId(null);
        setAssessorForm(emptyAssessorForm);
      }
      setSharedLoginPasswords((current) => {
        const next = { ...current };
        delete next[assessor.id];
        return next;
      });
      setTeamAssignments((current) =>
        Object.fromEntries(
          Object.entries(current).map(([facilityId, assignment]) => [
            facilityId,
            {
              leadId: assignment.leadId === assessor.id ? "" : assignment.leadId,
              memberIds: assignment.memberIds.filter((memberId) => memberId !== assessor.id),
            },
          ]),
        ),
      );
      if (round) {
        await loadRound(round.id);
      }
      setMessage("Shared group login deleted and removed from facility assignments everywhere.");
    } catch {
      setFormError("Unable to delete this shared group login right now.");
    } finally {
      setDeletingAssessorId(null);
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
          return assessmentAssignmentService.saveTeamMembers(assessmentFacility.id, {
            team_members: [
              {
                user_id: team.leadId,
                team_role: "TEAM_LEAD",
                can_enter_data: true,
                can_submit: true,
              },
            ],
          });
        }),
      );
      await loadRound(round.id);
      setActiveStep(4);
      setMessage("Shared group logins assigned to facilities.");
    } catch {
      setFormError("Unable to save shared group login assignments.");
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
      setMessage("Assessment round published successfully. Other assessor emails were deactivated so only the shared group accounts remain active.");
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

  const syncDhis2Values = async () => {
    if (!round) {
      return;
    }
    setSyncingDhis2(true);
    setFormError(null);
    setMessage(null);
    try {
      const response = await assessmentRoundService.syncDhis2Values(round.id);
      setMessage(
        `DHIS2 pre-sync complete: ${response.synced_facilities} facilit${response.synced_facilities === 1 ? "y" : "ies"} synced, ${response.failed_facilities} failed.`,
      );
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Unable to sync DHIS2 values for this assessment.");
    } finally {
      setSyncingDhis2(false);
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
          <Badge tone="success">{round ? round.assessment_code : "Assessment number assigned after save"}</Badge>
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
                onChange={(event) => {
                  const periodType = event.target.value as PeriodType;
                  setForm({
                    ...form,
                    period_type: periodType,
                    reporting_period: deriveReportingPeriod(periodType, form.start_date, form.end_date, form.reporting_period),
                  });
                }}
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
                The DHIS2 period code is generated automatically from the dates and period type. You normally do not need to type it.
              </p>
              <div className="mt-4 grid gap-4 md:grid-cols-3">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-brand-text">DHIS2 period code</label>
                  <Input
                    placeholder="Auto-generated, e.g. 202603"
                    value={form.reporting_period}
                    readOnly={form.period_type !== "CUSTOM"}
                    onChange={(event) => setForm({ ...form, reporting_period: event.target.value })}
                  />
                  <p className="mt-2 text-xs text-brand-muted">
                    {form.period_type === "CUSTOM"
                      ? "Custom periods are editable if DHIS2 requires a special code."
                      : "Generated from the start date for DHIS2 syncing."}
                  </p>
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-brand-text">Start date</label>
                  <Input
                    type="date"
                    value={form.start_date ?? ""}
                    onChange={(event) => {
                      const startDate = event.target.value || null;
                      setForm({
                        ...form,
                        start_date: startDate,
                        reporting_period: deriveReportingPeriod(form.period_type, startDate, form.end_date, form.reporting_period),
                      });
                    }}
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-brand-text">End date</label>
                  <Input
                    type="date"
                    value={form.end_date ?? ""}
                    onChange={(event) => {
                      const endDate = event.target.value || null;
                      setForm({
                        ...form,
                        end_date: endDate,
                        reporting_period: deriveReportingPeriod(form.period_type, form.start_date, endDate, form.reporting_period),
                      });
                    }}
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
          <Card title="Step 2: Select indicators" subtitle="Search DHIS2 directly, import the exact HMIS 105 data elements, and add them to this assessment.">
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
                  Start typing at least 2 characters to search DHIS2 and any data elements already imported into this assessment system.
                </div>
              ) : filteredIndicators.length === 0 && dhis2IndicatorResults.length === 0 && !searchingDhis2Indicators ? (
                <div className="rounded-2xl border border-dashed border-brand-border bg-brand-surface p-5 text-sm text-brand-muted">
                  No DHIS2 data elements matched this search. Confirm the DHIS2 sign-in in Settings, then try HMIS code, UID, or data element name.
                </div>
              ) : null}

              {filteredIndicators.map((indicator) => {
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
                          <Badge tone="success">Imported</Badge>
                        </div>
                        <p className="mt-2 text-sm text-brand-muted">
                          {indicator.indicator_group}
                          {indicator.hmis_section ? ` - ${indicator.hmis_section}` : ""}
                          {indicator.source_register ? ` - ${indicator.source_register}` : ""}
                        </p>
                        <p className="mt-1 break-all text-xs text-brand-muted">{indicator.dhis2_uid_or_operand}</p>
                      </div>
                    </label>
                  );
                })}

              {indicatorSearch.trim().length >= 2 ? (
                <div className="rounded-2xl border border-cyan-100 bg-cyan-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-brand-navy">DHIS2 search results</p>
                      <p className="mt-1 text-xs text-brand-muted">Import a result to make it selectable for this assessment.</p>
                    </div>
                    {searchingDhis2Indicators ? <Badge tone="info">Searching...</Badge> : null}
                  </div>
                  <div className="mt-3 space-y-2">
                    {dhis2IndicatorResults.map((result) => {
                      const alreadyLocal = availableIndicators.some(
                        (item) => item.dhis2_uid_or_operand === result.dhis2_uid_or_operand,
                      );
                      return (
                        <div key={result.dhis2_uid_or_operand} className="rounded-xl border border-white bg-white p-3">
                          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <p className="font-semibold text-brand-text">{result.name}</p>
                                <Badge tone="info">{result.hmis_code ?? result.data_element_uid}</Badge>
                                {alreadyLocal || result.already_imported ? <Badge tone="success">Already imported</Badge> : null}
                              </div>
                              <p className="mt-1 text-sm text-brand-muted">{result.dataset_name ?? "Dataset not shown by DHIS2"}</p>
                              <p className="mt-1 break-all text-xs text-brand-muted">{result.dhis2_uid_or_operand}</p>
                            </div>
                            <Button
                              className="shrink-0 px-3 py-2 text-xs"
                              onClick={() => void importAndSelectIndicator(result)}
                              disabled={!canEditDraft || importingIndicatorUid === result.dhis2_uid_or_operand}
                            >
                              {importingIndicatorUid === result.dhis2_uid_or_operand
                                ? "Importing..."
                                : alreadyLocal || result.already_imported
                                  ? "Add to assessment"
                                  : "Import and add"}
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                    {!searchingDhis2Indicators && dhis2IndicatorResults.length === 0 ? (
                      <p className="rounded-xl bg-white px-3 py-3 text-sm text-brand-muted">
                        No live DHIS2 results yet for this search.
                      </p>
                    ) : null}
                  </div>
                </div>
              ) : null}
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
          <Card title="Step 3: Select facilities" subtitle="Search DHIS2 directly, import the facility, and include it in this assessment round.">
            <Input
              placeholder="Search by facility, district, type, or DHIS2 UID"
              value={facilitySearch}
              onChange={(event) => setFacilitySearch(event.target.value)}
            />
            {facilitySearch.trim().length < 2 ? (
              <div className="mt-4 rounded-2xl border border-dashed border-brand-border bg-brand-surface p-5 text-sm text-brand-muted">
                Start typing at least 2 characters to search DHIS2 and any facilities already imported into this assessment system.
              </div>
            ) : filteredFacilities.length === 0 && dhis2FacilityResults.length === 0 && !searchingDhis2Facilities ? (
              <div className="mt-4 rounded-2xl border border-dashed border-brand-border bg-brand-surface p-5 text-sm text-brand-muted">
                No DHIS2 facilities matched this search. Confirm the DHIS2 sign-in in Settings, then try facility name, code, district, or UID.
              </div>
            ) : null}

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
                        DHIS2 org unit UID: {facility.dhis2_org_unit_uid ?? "Missing DHIS2 UID"}
                      </p>
                    </div>
                  </label>
              ))}

              {facilitySearch.trim().length >= 2 ? (
                <div className="rounded-2xl border border-cyan-100 bg-cyan-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-brand-navy">DHIS2 facility results</p>
                      <p className="mt-1 text-xs text-brand-muted">Import a result to include it in this assessment round.</p>
                    </div>
                    {searchingDhis2Facilities ? <Badge tone="info">Searching...</Badge> : null}
                  </div>
                  <div className="mt-3 space-y-2">
                    {dhis2FacilityResults.map((result) => {
                      const alreadyLocal = availableFacilities.some(
                        (item) => item.dhis2_org_unit_uid === result.dhis2_org_unit_uid,
                      );
                      return (
                        <div key={result.dhis2_org_unit_uid} className="rounded-xl border border-white bg-white p-3">
                          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <p className="font-semibold text-brand-text">{result.facility_name}</p>
                                <Badge tone="info">{result.district}</Badge>
                                <Badge tone="neutral">{result.facility_type}</Badge>
                                {alreadyLocal || result.already_imported ? <Badge tone="success">Already imported</Badge> : null}
                              </div>
                              <p className="mt-1 text-sm text-brand-muted">{result.dhis2_parent_name ?? "Parent not shown by DHIS2"}</p>
                              <p className="mt-1 break-all text-xs text-brand-muted">{result.dhis2_org_unit_uid}</p>
                            </div>
                            <Button
                              className="shrink-0 px-3 py-2 text-xs"
                              onClick={() => void importAndSelectFacility(result)}
                              disabled={!canEditDraft || importingFacilityUid === result.dhis2_org_unit_uid}
                            >
                              {importingFacilityUid === result.dhis2_org_unit_uid
                                ? "Importing..."
                                : alreadyLocal || result.already_imported
                                  ? "Add to assessment"
                                  : "Import and add"}
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                    {!searchingDhis2Facilities && dhis2FacilityResults.length === 0 ? (
                      <p className="rounded-xl bg-white px-3 py-3 text-sm text-brand-muted">
                        No live DHIS2 facility results yet for this search.
                      </p>
                    ) : null}
                  </div>
                </div>
              ) : null}
              </div>
            <div className="mt-5 flex gap-2">
              <Button onClick={() => void saveFacilities()} disabled={!canEditDraft || saving || !round}>
                {saving ? "Saving..." : "Save selected facilities"}
              </Button>
            </div>
          </Card>

          <Card title="Selected facilities" subtitle={`${selectedFacilityIds.length} facilities currently included in the round.`}>
            {selectedFacilityDetails.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-brand-border bg-brand-surface p-5 text-sm text-brand-muted">
                Search DHIS2, import facilities, and add them here before assigning shared group logins.
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
          <section className="rounded-[28px] border border-brand-border bg-[linear-gradient(135deg,#f5fbff,#eef8f4)] p-5 shadow-soft">
            <p className="text-[10px] uppercase tracking-[0.28em] text-brand-teal">Group access setup</p>
            <h2 className="mt-2 font-display text-2xl font-semibold text-brand-text">
              Create one shared login per field group, then assign it to one or more facilities.
            </h2>
            <p className="mt-2 max-w-3xl text-sm text-brand-muted">
              Each group can use one shared email and password. Anyone who signs in with the exact same credentials will
              open that group's assigned facilities in this assessment project and can continue editing the same work.
            </p>
          </section>

          <Card
            title="Step 4A: Create shared group login"
            subtitle="Create one login for the field group here, then reuse or edit that same shared account across one or more facilities below."
          >
            <div className="grid gap-4 lg:grid-cols-[1.3fr_0.7fr]">
              <div className="space-y-4">
                {editingAssessorId ? (
                  <div className="rounded-2xl border border-brand-border bg-brand-surface p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-muted">Editing shared group login</p>
                    <p className="mt-2 text-sm text-brand-text">
                      Current login email: <span className="font-semibold">{assessorForm.email}</span>
                    </p>
                    <p className="mt-1 text-sm text-brand-text">
                      Current password in this review session: <span className="font-semibold">{sharedLoginPasswords[editingAssessorId] ?? "Not available in this session. Enter a new password below to replace it."}</span>
                    </p>
                  </div>
                ) : null}
                <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
                  <div>
                    <label className="mb-2 block text-sm font-semibold text-brand-text">Group account name</label>
                    <Input
                      value={assessorForm.full_name}
                      onChange={(event) => setAssessorForm({ ...assessorForm, full_name: event.target.value })}
                      placeholder="Example: Masaka Team A"
                      disabled={!canEditTeams}
                    />
                  </div>
                  <div>
                    <label className="mb-2 block text-sm font-semibold text-brand-text">Shared login email</label>
                    <Input
                      type="email"
                      value={assessorForm.email}
                      onChange={(event) => setAssessorForm({ ...assessorForm, email: event.target.value })}
                      placeholder="group-login@example.org"
                      disabled={!canEditTeams}
                    />
                  </div>
                </div>
                <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
                  <div>
                    <label className="mb-2 block text-sm font-semibold text-brand-text">
                      Shared password {editingAssessorId ? "(leave blank to keep current password)" : ""}
                    </label>
                    <Input
                      type="text"
                      value={assessorForm.password ?? ""}
                      onChange={(event) => setAssessorForm({ ...assessorForm, password: event.target.value })}
                      placeholder="Minimum 8 characters"
                      disabled={!canEditTeams}
                    />
                    <p className="mt-2 text-xs text-brand-muted">
                      This password stays visible to the manager during setup and review for this browser session.
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={() => void createAssessorInline()} disabled={!canEditTeams || creatingAssessor}>
                      {creatingAssessor ? (editingAssessorId ? "Saving..." : "Creating...") : editingAssessorId ? "Save changes" : "Create shared login"}
                    </Button>
                    {editingAssessorId ? (
                      <Button
                        variant="secondary"
                        onClick={() => {
                          setEditingAssessorId(null);
                          setAssessorForm(emptyAssessorForm);
                          setFormError(null);
                        }}
                        disabled={!canEditTeams || creatingAssessor}
                      >
                        Cancel
                      </Button>
                    ) : null}
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-brand-border bg-brand-surface p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-muted">Available shared logins</p>
                <p className="mt-3 text-3xl font-bold text-brand-navy">{assessors.length}</p>
                <p className="mt-2 text-sm text-brand-muted">
                  Any active shared login created here can be assigned to one or many facilities in this assessment project.
                </p>
                <div className="mt-4 space-y-2">
                  {assessors.slice(0, 6).map((assessor) => (
                    <div key={assessor.id} className="rounded-xl bg-white px-3 py-2 text-sm text-brand-text">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold">{assessor.full_name}</p>
                          <p className="text-xs text-brand-muted">{assessor.email}</p>
                          <p className="mt-1 text-xs text-brand-text">
                            Password: {sharedLoginPasswords[assessor.id] ?? "Not available in this session"}
                          </p>
                          <p className="mt-1 text-xs text-brand-muted">
                            Assigned to {sharedLoginUsageCounts[assessor.id] ?? 0} {sharedLoginUsageCounts[assessor.id] === 1 ? "facility" : "facilities"}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="secondary"
                            className="px-3 py-2 text-xs"
                            onClick={() => startEditingAssessor(assessor)}
                            disabled={!canEditTeams || deletingAssessorId === assessor.id}
                          >
                            Edit
                          </Button>
                          <Button
                            variant="ghost"
                            className="px-3 py-2 text-xs text-brand-danger"
                            onClick={() => void deleteAssessorInline(assessor)}
                            disabled={!canEditTeams || deletingAssessorId === assessor.id}
                          >
                            {deletingAssessorId === assessor.id ? "Deleting..." : "Delete"}
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                  {assessors.length === 0 ? (
                    <div className="rounded-xl bg-white px-3 py-2 text-sm text-brand-muted">
                      No shared group logins yet.
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </Card>

          <Card
            title="Step 4B: Assign shared login to facilities"
            subtitle="Choose which shared group credentials should open each selected facility assessment. The same login can be reused on multiple facilities."
          >
          {selectedFacilityDetails.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-brand-border bg-brand-surface p-5 text-sm text-brand-muted">
              No facilities selected yet. Go back one step and add facilities first.
            </div>
          ) : assessors.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-brand-border bg-brand-surface p-5 text-sm text-brand-muted">
              No active shared logins exist yet. First use Step 4A above to create at least one shared group account.
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
                        Shared login required
                      </div>
                    ) : null}
                  </div>
                  <div className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand-muted">
                      Shared group login
                    </p>
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
                      <option value="">Select shared login</option>
                      {assessors.map((assessor) => (
                        <option key={assessor.id} value={assessor.id}>
                          {assessor.full_name} - {assessor.email}
                        </option>
                      ))}
                    </Select>
                    <p className="text-xs text-brand-muted">
                      Everyone in that field group should use these exact credentials. This same group login can also be assigned to other facilities in the same project.
                    </p>
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
        <div className="space-y-6">
          <Card title="Step 5: Review and publish" subtitle="Review one long checklist of the entire project. Every section can still be edited before publishing.">
            <div className="space-y-5">
              <div className="rounded-2xl bg-brand-navy p-5 text-white">
                <p className="text-sm text-slate-200">Assessment package readiness</p>
                <p className="mt-2 text-2xl font-bold">
                  {round?.status === "PUBLISHED" ? "Ready for assessors" : "Draft package in progress"}
                </p>
                <p className="mt-2 text-sm text-slate-200">
                  Review everything below. If anything needs to change, use the Edit button in that section, update it, and return here before publishing.
                </p>
              </div>

              <section className="rounded-2xl border border-brand-border bg-white p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-brand-text">1. Basic project details</p>
                    <p className="mt-1 text-sm text-brand-muted">Name, reporting period, dates, deadline, description, and notes.</p>
                  </div>
                  <Button variant="secondary" onClick={() => setActiveStep(0)} disabled={!canEditDraft}>
                    Edit
                  </Button>
                </div>
                <div className="mt-4 space-y-2 text-sm text-brand-text">
                  <div className="rounded-xl bg-brand-surface px-3 py-2"><span className="font-semibold">Assessment name:</span> {form.name}</div>
                  <div className="rounded-xl bg-brand-surface px-3 py-2"><span className="font-semibold">Reporting period:</span> {form.reporting_period}</div>
                  <div className="rounded-xl bg-brand-surface px-3 py-2"><span className="font-semibold">Period type:</span> {form.period_type}</div>
                  <div className="rounded-xl bg-brand-surface px-3 py-2"><span className="font-semibold">Start date:</span> {form.start_date ?? "Not set"}</div>
                  <div className="rounded-xl bg-brand-surface px-3 py-2"><span className="font-semibold">End date:</span> {form.end_date ?? "Not set"}</div>
                  <div className="rounded-xl bg-brand-surface px-3 py-2"><span className="font-semibold">Deadline:</span> {form.deadline ?? "No deadline set"}</div>
                  <div className="rounded-xl bg-brand-surface px-3 py-2"><span className="font-semibold">Description:</span> {form.description?.trim() || "No description provided"}</div>
                  <div className="rounded-xl bg-brand-surface px-3 py-2"><span className="font-semibold">Notes:</span> {form.notes?.trim() || "No notes provided"}</div>
                </div>
              </section>

              <section className="rounded-2xl border border-brand-border bg-white p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-brand-text">2. Indicators</p>
                    <p className="mt-1 text-sm text-brand-muted">{selectedIndicatorDetails.length} indicators included in this project.</p>
                  </div>
                  <Button variant="secondary" onClick={() => setActiveStep(1)} disabled={!canEditDraft}>
                    Edit
                  </Button>
                </div>
                <div className="mt-4 space-y-2">
                  {selectedIndicatorDetails.map(({ indicator, selection }, index) => (
                    <div key={indicator.id} className="rounded-xl bg-brand-surface px-3 py-3 text-sm text-brand-text">
                      <p className="font-semibold">{index + 1}. {indicator.indicator_name}</p>
                      <p className="mt-1 text-brand-muted">{indicator.hmis_code} | {indicator.indicator_group} | {indicator.hmis_section ?? "No section"}</p>
                      <p className="mt-1 text-brand-muted">
                        Required: {selection.is_required ? "Yes" : "No"} | Custom threshold: {selection.custom_threshold_percent ?? "Default"}
                      </p>
                      <p className="mt-1 text-brand-muted">Notes: {selection.notes?.trim() || "No indicator notes"}</p>
                    </div>
                  ))}
                </div>
              </section>

              <section className="rounded-2xl border border-brand-border bg-white p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-brand-text">3. Facilities</p>
                    <p className="mt-1 text-sm text-brand-muted">{selectedFacilityDetails.length} facilities included in this project.</p>
                  </div>
                  <Button variant="secondary" onClick={() => setActiveStep(2)} disabled={!canEditDraft}>
                    Edit
                  </Button>
                </div>
                <div className="mt-4 space-y-2">
                  {selectedFacilityDetails.map((facility, index) => (
                    <div key={facility.id} className="rounded-xl bg-brand-surface px-3 py-3 text-sm text-brand-text">
                      <p className="font-semibold">{index + 1}. {facility.facility_name}</p>
                      <p className="mt-1 text-brand-muted">{facility.district} | {facility.facility_type} | {facility.ownership}</p>
                      <p className="mt-1 break-all text-brand-muted">DHIS2 UID: {facility.dhis2_org_unit_uid ?? "Missing DHIS2 UID"}</p>
                    </div>
                  ))}
                </div>
              </section>

              <section className="rounded-2xl border border-brand-border bg-white p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-brand-text">4. Shared group logins and facility assignments</p>
                    <p className="mt-1 text-sm text-brand-muted">Every shared login, its email, and each facility it opens.</p>
                  </div>
                  <Button variant="secondary" onClick={() => setActiveStep(3)} disabled={!canEditTeams}>
                    Edit
                  </Button>
                </div>
                <div className="mt-4 space-y-3">
                  {assessors.length === 0 ? (
                    <div className="rounded-xl bg-brand-surface px-3 py-3 text-sm text-brand-muted">
                      No shared group logins created yet.
                    </div>
                  ) : (
                    assessors.map((assessor) => (
                      <div key={assessor.id} className="rounded-xl bg-brand-surface px-3 py-3 text-sm text-brand-text">
                        <p className="font-semibold">{assessor.full_name}</p>
                        <p className="mt-1 text-brand-muted">Login email: {assessor.email}</p>
                        <p className="mt-1 text-brand-muted">
                          Password: {sharedLoginPasswords[assessor.id] ?? "Not available in this session"}
                        </p>
                        <p className="mt-1 text-brand-muted">
                          Assigned facilities: {sharedLoginUsageCounts[assessor.id] ?? 0}
                        </p>
                      </div>
                    ))
                  )}
                  {reviewFacilityAssignments.map(({ facility, assignedLogin }) => (
                    <div key={facility.id} className="rounded-xl border border-brand-border/70 bg-white px-3 py-3 text-sm text-brand-text">
                      <p className="font-semibold">{facility.facility_name}</p>
                      <p className="mt-1 text-brand-muted">
                        Shared login: {assignedLogin ? `${assignedLogin.full_name} (${assignedLogin.email})` : "Not assigned"}
                      </p>
                    </div>
                  ))}
                </div>
              </section>

              <section className="rounded-2xl border border-brand-border bg-white p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-brand-text">5. Source document requirements</p>
                    <p className="mt-1 text-sm text-brand-muted">Documents required during field assessment.</p>
                  </div>
                  <Button variant="secondary" onClick={() => setActiveStep(0)} disabled={!canEditDraft}>
                    Edit
                  </Button>
                </div>
                <div className="mt-4 space-y-2">
                  {(round?.source_document_requirements ?? []).map((item, index) => (
                    <div key={item.id} className="rounded-xl bg-brand-surface px-3 py-3 text-sm text-brand-text">
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-semibold">{index + 1}. {item.name}</span>
                        <Badge tone={item.is_required ? "success" : "neutral"}>
                          {item.is_required ? "Required" : "Optional"}
                        </Badge>
                      </div>
                      <p className="mt-1 text-brand-muted">{item.description?.trim() || "No description provided."}</p>
                    </div>
                  ))}
                </div>
              </section>

              <section className="rounded-2xl border border-brand-border bg-white p-4">
                <p className="text-sm font-semibold text-brand-text">6. Publishing controls</p>
                <div className="mt-4 space-y-3">
                  <div className="rounded-xl bg-brand-surface px-3 py-3 text-sm text-brand-text">
                    <p className="font-semibold">Selected indicators</p>
                    <p className="mt-1 text-brand-muted">{selectedIndicators.length}</p>
                  </div>
                  <div className="rounded-xl bg-brand-surface px-3 py-3 text-sm text-brand-text">
                    <p className="font-semibold">Selected facilities</p>
                    <p className="mt-1 text-brand-muted">{selectedFacilityIds.length}</p>
                  </div>
                  <div className="rounded-xl bg-brand-surface px-3 py-3 text-sm text-brand-text">
                    <p className="font-semibold">Facilities with assigned group login</p>
                    <p className="mt-1 text-brand-muted">
                      {selectedFacilityIds.filter((facilityId) => Boolean(teamAssignments[facilityId]?.leadId)).length}
                    </p>
                  </div>
                  <div className="rounded-xl bg-brand-surface px-3 py-3 text-sm text-brand-text">
                    <p className="font-semibold">Unassigned facilities</p>
                    <p className="mt-1 text-brand-muted">
                      {selectedFacilityIds.filter((facilityId) => !teamAssignments[facilityId]?.leadId).length}
                    </p>
                  </div>
                  <div className="rounded-xl bg-brand-surface px-3 py-3 text-sm text-brand-text">
                    <div className="flex items-center gap-2 text-brand-muted">
                      <CheckCircle2 size={16} />
                      Offline preparation
                    </div>
                    <p className="mt-2 text-brand-text">
                      Pre-sync DHIS2 values before publishing so group members see system figures as soon as they open their assigned assessment.
                    </p>
                  </div>
                  <label className="flex items-center gap-2 text-sm text-brand-text">
                    <input
                      type="checkbox"
                      checked={allowUnassignedPublish}
                      onChange={(event) => setAllowUnassignedPublish(event.target.checked)}
                      disabled={!canEditDraft}
                    />
                    Allow publishing even if some facilities still have no shared group login
                  </label>
                </div>
              </section>
            </div>

            <div className="mt-6 flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={() => void syncDhis2Values()}
                disabled={!isManager || syncingDhis2 || !round || selectedIndicators.length === 0 || selectedFacilityIds.length === 0}
              >
                {syncingDhis2 ? "Syncing DHIS2..." : "Pre-sync DHIS2 values"}
              </Button>
              <Button variant="danger" onClick={() => void publishRound()} disabled={!canEditDraft || saving || !round}>
                {saving ? "Publishing..." : "Publish round"}
              </Button>
              {round ? (
                <Button variant="secondary" onClick={() => void closeRound()} disabled={!isManager || saving}>
                  Close round
                </Button>
              ) : null}
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
