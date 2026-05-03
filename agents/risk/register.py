"""Risk register following ISO 31000 severity × likelihood matrix."""
from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass
from enum import IntEnum
from typing import List


class Severity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class Likelihood(IntEnum):
    RARE = 1
    UNLIKELY = 2
    POSSIBLE = 3
    LIKELY = 4
    ALMOST_CERTAIN = 5


@dataclass
class RiskItem:
    id: str
    category: str       # supply | regulatory | technical
    description: str
    severity: int       # 1–4 per ISO 31000
    likelihood: int     # 1–5 per ISO 31000
    risk_score: int     # severity × likelihood
    mitigation: str

    def to_dict(self) -> dict:
        return asdict(self)


_RAW_RISKS: list[dict] = [
    {
        "id": "SUP-001",
        "category": "supply",
        "description": (
            "Single-source dependency on imported power semiconductors (IGBT/MOSFET); "
            "port disruption or export restriction halts production."
        ),
        "severity": Severity.HIGH,
        "likelihood": Likelihood.POSSIBLE,
        "mitigation": (
            "Qualify second-source equivalent; maintain 6-week safety stock "
            "in bonded warehouse under MOOWR scheme."
        ),
    },
    {
        "id": "SUP-002",
        "category": "supply",
        "description": (
            "Long lead-time PCB laminates (Rogers/Taconic) with 12–16 week delivery; "
            "demand surge causes shortage."
        ),
        "severity": Severity.HIGH,
        "likelihood": Likelihood.UNLIKELY,
        "mitigation": (
            "Blanket PO with authorised distributor; design compatible footprint "
            "for alternate material grade."
        ),
    },
    {
        "id": "SUP-003",
        "category": "supply",
        "description": "Foreign exchange rate fluctuation increases landed cost beyond project budget.",
        "severity": Severity.MEDIUM,
        "likelihood": Likelihood.LIKELY,
        "mitigation": (
            "Hedge INR/USD exposure via forward contracts; build 10% FX buffer "
            "in BOM cost model computed by karaveda MCP."
        ),
    },
    {
        "id": "SUP-004",
        "category": "supply",
        "description": (
            "Counterfeit components supplied by unauthorised channel partners "
            "leading to field failures."
        ),
        "severity": Severity.CRITICAL,
        "likelihood": Likelihood.UNLIKELY,
        "mitigation": (
            "Procure only from franchised distributors (Mouser/DigiKey/Element14); "
            "100% incoming inspection with certificate of conformance for critical parts."
        ),
    },
    {
        "id": "SUP-005",
        "category": "supply",
        "description": (
            "Logistics delays at Indian customs clearing due to incomplete "
            "BoE documentation for specialised test equipment."
        ),
        "severity": Severity.MEDIUM,
        "likelihood": Likelihood.POSSIBLE,
        "mitigation": (
            "Engage experienced CHA (Customs House Agent); pre-validate HSN codes "
            "and duty amounts via karaveda customs_calc before shipment."
        ),
    },
    {
        "id": "REG-001",
        "category": "regulatory",
        "description": "CBIC revises BCD rate on imported solar testing equipment HSN chapters.",
        "severity": Severity.HIGH,
        "likelihood": Likelihood.POSSIBLE,
        "mitigation": (
            "Use karaveda customs_calc dynamically at proposal time; "
            "include price-revision clause in customer contracts."
        ),
    },
    {
        "id": "REG-002",
        "category": "regulatory",
        "description": (
            "IEC 61215 standard amendment requires retesting of approved designs, "
            "delaying product shipment."
        ),
        "severity": Severity.HIGH,
        "likelihood": Likelihood.UNLIKELY,
        "mitigation": (
            "Subscribe to IEC standards alert service; design with modular optics "
            "to enable quick optical sub-system recertification."
        ),
    },
    {
        "id": "REG-003",
        "category": "regulatory",
        "description": (
            "BIS CRS mandatory certification delay for test equipment sub-assemblies "
            "imported under a new product category."
        ),
        "severity": Severity.MEDIUM,
        "likelihood": Likelihood.POSSIBLE,
        "mitigation": (
            "Engage BIS consultant 6 months before launch; qualify Indian-made "
            "substitute components that bypass BIS import requirements."
        ),
    },
    {
        "id": "REG-004",
        "category": "regulatory",
        "description": (
            "IGST exemption removal on R&D imports currently benefiting "
            "imported light sources and calibration standards."
        ),
        "severity": Severity.MEDIUM,
        "likelihood": Likelihood.RARE,
        "mitigation": (
            "Monitor DGFT and MeitY notifications; factor worst-case IGST "
            "in project NPV and offer customer price lock for 12 months."
        ),
    },
    {
        "id": "TECH-001",
        "category": "technical",
        "description": (
            "Spectral non-uniformity across 2 m × 1.3 m illumination plane "
            "fails IEC Class AAA ±25% spatial uniformity tolerance."
        ),
        "severity": Severity.CRITICAL,
        "likelihood": Likelihood.POSSIBLE,
        "mitigation": (
            "Perform CFD/ray-trace simulation pre-build using ShilpaSutra cfd_run; "
            "iterate optical diffuser design until model predicts <20% non-uniformity."
        ),
    },
    {
        "id": "TECH-002",
        "category": "technical",
        "description": (
            "Thermal runaway in high-current bus bars during 200 A continuous "
            "irradiance cycle causes insulation failure."
        ),
        "severity": Severity.CRITICAL,
        "likelihood": Likelihood.UNLIKELY,
        "mitigation": (
            "Copper bus bar thermal FMEA via mcp-suryaprajna; "
            "derate to 80% of rated current; add PTC fuses."
        ),
    },
    {
        "id": "TECH-003",
        "category": "technical",
        "description": (
            "Firmware timing jitter in DAQ sampling exceeds 1 ms measurement "
            "uncertainty budget, invalidating IEC 60904-9 compliance."
        ),
        "severity": Severity.MEDIUM,
        "likelihood": Likelihood.POSSIBLE,
        "mitigation": (
            "Use hardware-triggered DMA on spanda-daq; validate timing "
            "with NIST-traceable time reference during FAT."
        ),
    },
]


def build_risk_register() -> List[RiskItem]:
    """Return ISO 31000 risk register with severity × likelihood scoring."""
    items: List[RiskItem] = []
    for r in _RAW_RISKS:
        sev = int(r["severity"])
        lkh = int(r["likelihood"])
        items.append(
            RiskItem(
                id=r["id"],
                category=r["category"],
                description=r["description"],
                severity=sev,
                likelihood=lkh,
                risk_score=sev * lkh,
                mitigation=r["mitigation"],
            )
        )
    return items


def register_to_json(items: List[RiskItem]) -> str:
    """Serialise risk register to JSON string."""
    return json.dumps([i.to_dict() for i in items], indent=2)


def register_to_csv(items: List[RiskItem]) -> str:
    """Serialise risk register to CSV string."""
    if not items:
        return ""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(items[0].to_dict().keys()))
    w.writeheader()
    for item in items:
        w.writerow(item.to_dict())
    return buf.getvalue()
