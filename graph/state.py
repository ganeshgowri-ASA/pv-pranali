from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict


class PipelineState(TypedDict):
    # Core orchestration fields
    intent: str
    proposal_id: str
    run_id: str
    current_node: str
    awaiting_human: bool
    gate_name: Optional[str]
    completed_nodes: Annotated[List[str], operator.add]  # reducer: append across updates
    tokens_used: int
    error: Optional[str]

    # Stage output fields
    research_data: Dict[str, Any]
    standards_data: Dict[str, Any]
    bom: List[Dict[str, Any]]
    cad_artifacts: Dict[str, Any]
    ecad_artifacts: Dict[str, Any]
    pcb_artifacts: Dict[str, Any]
    bom_impact_data: Dict[str, Any]
    risk_swot_data: Dict[str, Any]
    rfq_drafts: List[Dict[str, Any]]
    proposal_doc: Dict[str, Any]
    pitch_doc: Dict[str, Any]
    landing_url: Optional[str]
    linkedin_draft: Optional[str]
