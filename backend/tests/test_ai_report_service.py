from app.services.ai_report_service import _finding_blocks_to_markdown, _normalize_finding_blocks, _try_parse_sections


def test_v4_finding_block_json_parses_and_renders_markdown() -> None:
    raw = """
    {
      "executive_snapshot": {
        "headline": "DQA review",
        "primary_finding": "Overall score requires follow-up.",
        "management_implication": "Management should prioritize critical rows.",
        "urgent_actions": ["Reconcile death rows"]
      },
      "scope_and_method": {
        "scope_summary": "One facility was assessed.",
        "method_summary": "Three sources were compared.",
        "denominator_note": "One row.",
        "severity_note": "Critical rows first."
      },
      "critical_chase_list_intro": "Review critical rows.",
      "findings": [
        {
          "finding_number": 1,
          "finding_title": "DHIS2 no-data requires verification",
          "finding_category": "DHIS2",
          "evidence": "One no-data row.",
          "interpretation": "No-data is not zero.",
          "affected_facilities": ["Facility A"],
          "affected_indicators": ["Newborn deaths"],
          "affected_administrative_areas": ["Area A"],
          "risk_level": "Critical",
          "implication": "Requires reconciliation.",
          "required_action": "Verify DHIS2.",
          "owner_role": "MoH DHIS2 Team",
          "proposed_timeline": "Within 30 days",
          "evidence_required_for_closure": "DHIS2 screenshot."
        }
      ],
      "dhis2_no_data_review": {},
      "source_document_review": {},
      "facility_performance_summary": {},
      "indicator_performance_summary": {},
      "root_cause_synthesis": {},
      "corrective_action_plan": {"summary": "Act.", "actions": []},
      "limitations": ["Source documents not assessed"],
      "next_round_improvements": ["Add checklist"],
      "conclusion": "Ready for review."
    }
    """
    parsed = _try_parse_sections(raw)
    assert parsed is not None
    blocks = _normalize_finding_blocks(parsed)
    markdown = _finding_blocks_to_markdown(blocks)
    assert "Finding 1: DHIS2 no-data requires verification" in markdown
    assert "Evidence required for closure: DHIS2 screenshot." in markdown
