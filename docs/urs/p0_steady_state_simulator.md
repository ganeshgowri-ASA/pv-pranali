<!-- CONFIDENTIAL — Reliance Industries Ltd — Not for distribution -->

# P0 — BBA Steady-State Sun Simulator
## URS Reference: iRIL-MxML-FRM-GE-003-Rev00

> **CONFIDENTIAL**: This document contains customer requirements provided by
> Reliance Industries Ltd, Module R&D Laboratory. Distribution restricted to
> project team under NDA.

---

## 1. Performance Requirements

### PERF-001 — Irradiance Range
**Section**: Performance
**Priority**: Must
**Text**: The sun simulator shall provide stable irradiance between 700 W/m²
and 1300 W/m² at the measurement plane.
**Acceptance criterion**: Measured irradiance (calibrated reference cell, ISO 9060
Class A) within ±2% of setpoint over full range.
**Linked standard**: IEC 60904-9:2020 §5.3

### PERF-002 — Spatial Non-Uniformity
**Section**: Performance
**Priority**: Must
**Text**: Spatial non-uniformity of irradiance over the test area shall be
Class A+ per IEC 60904-9:2020.
**Acceptance criterion**: Non-uniformity ≤2% measured per IEC 60904-9:2020
Annex A over 2-module test plane (2000 × 1100 mm).
**Linked standard**: IEC 60904-9:2020 §5.2

### PERF-003 — Temporal Instability
**Section**: Performance
**Priority**: Must
**Text**: Temporal instability of irradiance shall be Class A+ per IEC 60904-9:2020.
**Acceptance criterion**: Temporal instability ≤2% over I-V measurement window.
**Linked standard**: IEC 60904-9:2020 §5.4

### PERF-004 — Spectral Match
**Section**: Performance
**Priority**: Must
**Text**: Spectral irradiance distribution shall match AM1.5G (IEC 60904-3)
with Class A+ spectral match per IEC 60904-9:2020.
**Acceptance criterion**: Spectral match factor within 0.875–1.125 in each of
the 6 wavelength intervals per IEC 60904-9:2020 Table 1.
**Linked standard**: IEC 60904-9:2020 §5.1, IEC 60904-3

### PERF-005 — Module Capacity
**Section**: Performance
**Priority**: Must
**Text**: The simulator shall accommodate two full-size commercial PV modules
simultaneously.
**Acceptance criterion**: Test area ≥ 2000 × 1100 mm; both modules measurable
in single setup.
**Linked standard**: —

### PERF-006 — Temperature Range
**Section**: Performance
**Priority**: Must
**Text**: Module/cell temperature shall be controllable between 20 °C and 75 °C.
**Acceptance criterion**: Setpoint stability ±0.5 °C; measured by calibrated
Pt-100 (IEC 60751 Class AA) in contact with module backsheet.
**Linked standard**: IEC 60891, IEC 60751

### PERF-007 — I-V Measurement
**Section**: Performance
**Priority**: Must
**Text**: Full I-V curve measurement using 4-wire Kelvin connection per IEC 60904-1.
**Acceptance criterion**: Isc uncertainty ≤0.5%, Voc uncertainty ≤0.3%, Pmax
uncertainty ≤1.5% (k=2, per ISO/IEC 17025).
**Linked standard**: IEC 60904-1, IEC 60891

---

## 2. Safety Requirements

### SAFE-001 — Electrical Safety
**Section**: Safety
**Priority**: Must
**Text**: Equipment shall comply with IEC 61010-1 for laboratory electrical safety.
**Acceptance criterion**: Third-party IEC 61010-1 test report or CE declaration.
**Linked standard**: IEC 61010-1

### SAFE-002 — Machine Safety
**Section**: Safety
**Priority**: Must
**Text**: Electrical equipment shall comply with IEC 60204-1.
**Acceptance criterion**: IEC 60204-1 checklist signed off; E-stop functional test passed.
**Linked standard**: IEC 60204-1

### SAFE-003 — Enclosure Protection
**Section**: Safety
**Priority**: Must
**Text**: Enclosure protection rating shall be ≥IP54.
**Acceptance criterion**: IP54 certificate or test record per IEC 60529.
**Linked standard**: IEC 60529

### SAFE-004 — UV Safety
**Section**: Safety
**Priority**: Must (LED variant) / Should (MH variant)
**Text**: UV radiation from lamp/LED shall be shielded to safe levels at
operator position.
**Acceptance criterion**: UV irradiance at operator position < ICNIRP limits.
**Linked standard**: IEC 62471 (photobiological safety)

---

## 3. Utility Requirements

### UTIL-001 — Power Supply
**Section**: Utility
**Priority**: Must
**Text**: Equipment shall operate on 3-phase 415 V AC ±10%, 50 Hz ±2%, TN-S system.
**Acceptance criterion**: Verified by commissioning engineer; no de-rating required.
**Linked standard**: IS 732, IEC 60364

### UTIL-002 — Cooling
**Section**: Utility
**Priority**: Must
**Text**: Cooling system shall use refrigerant compliant with Montreal Protocol,
F-Gas (EU 517/2014), and ISO 817 / EN 378.
**Acceptance criterion**: Refrigerant data sheet and equipment conformity declaration.
**Linked standard**: ISO 817, EN 378, Montreal Protocol

---

## 4. Warranty Requirements

### WARR-001 — Warranty Period
**Section**: Warranty
**Priority**: Must
**Text**: Equipment shall carry a minimum 12-month on-site warranty from FAT date.
**Acceptance criterion**: Warranty certificate issued at FAT.
**Linked standard**: —

### WARR-002 — Spare Parts
**Section**: Warranty
**Priority**: Should
**Text**: Critical spare parts list (lamps, fuses, sensors) to be provided with equipment.
**Acceptance criterion**: Spare parts list and initial stock delivered with equipment.
**Linked standard**: —

---

## 5. KPI Requirements

### KPI-001 — Uptime
**Section**: KPI
**Priority**: Should
**Text**: Equipment uptime ≥95% during lab operating hours (8h/day, 5d/week).
**Acceptance criterion**: Uptime log reviewed at 6-month post-FAT review.
**Linked standard**: —

### KPI-002 — Calibration Interval
**Section**: KPI
**Priority**: Must
**Text**: Calibration interval for reference cell and sensors ≤12 months.
**Acceptance criterion**: Calibration schedule in IQ documentation.
**Linked standard**: ISO/IEC 17025:2017, ISO 10012

---

## 6. Calibration Requirements

### CAL-001 — Traceability
**Section**: Calibration
**Priority**: Must
**Text**: All measurement parameters shall be traceable to SI via NABL-accredited
or PTB/NIST-accredited calibration laboratory.
**Acceptance criterion**: Calibration certificates with unbroken traceability chain.
**Linked standard**: ISO/IEC 17025:2017, ISO 10012, VIM JCGM 200:2012

### CAL-002 — Reference Cell
**Section**: Calibration
**Priority**: Must
**Text**: Reference solar cell used for irradiance calibration shall be ISO 9060
Class A (or equivalent), calibrated by an accredited lab.
**Acceptance criterion**: Valid calibration certificate at FAT.
**Linked standard**: ISO 9060, IEC 60904-2

---

## 7. Shipping & Installation Requirements

### SHIP-001 — Packaging
**Section**: Shipping
**Priority**: Must
**Text**: Equipment shall be packaged to survive road transport within India
(ASTM D4169 or equivalent).
**Acceptance criterion**: No damage on receipt; inspection record signed.
**Linked standard**: ASTM D4169

### SHIP-002 — Installation Support
**Section**: Shipping
**Priority**: Must
**Text**: Supplier shall provide on-site installation and commissioning support.
**Acceptance criterion**: IQ/OQ/PQ completed and signed off on-site.
**Linked standard**: —

---

## 8. Supplier Requirements

### SUPP-001 — Quality System
**Section**: Supplier
**Priority**: Must
**Text**: Supplier shall hold ISO 9001:2015 certification or demonstrate
equivalent quality management.
**Acceptance criterion**: ISO 9001 certificate or quality plan accepted by RIL.
**Linked standard**: ISO 9001:2015

### SUPP-002 — RoHS/REACH
**Section**: Supplier
**Priority**: Must
**Text**: All components shall comply with RoHS 2011/65/EU and REACH EC 1907/2006.
**Acceptance criterion**: RoHS/REACH declarations for all components in BoM.
**Linked standard**: RoHS, REACH

---

## Requirements Summary

| Req-ID | Section | Priority | Status |
|--------|---------|----------|--------|
| PERF-001 | Performance | Must | Open |
| PERF-002 | Performance | Must | Open |
| PERF-003 | Performance | Must | Open |
| PERF-004 | Performance | Must | Open |
| PERF-005 | Performance | Must | Open |
| PERF-006 | Performance | Must | Open |
| PERF-007 | Performance | Must | Open |
| SAFE-001 | Safety | Must | Open |
| SAFE-002 | Safety | Must | Open |
| SAFE-003 | Safety | Must | Open |
| SAFE-004 | Safety | Must/Should | Open |
| UTIL-001 | Utility | Must | Open |
| UTIL-002 | Utility | Must | Open |
| WARR-001 | Warranty | Must | Open |
| WARR-002 | Warranty | Should | Open |
| KPI-001 | KPI | Should | Open |
| KPI-002 | KPI | Must | Open |
| CAL-001 | Calibration | Must | Open |
| CAL-002 | Calibration | Must | Open |
| SHIP-001 | Shipping | Must | Open |
| SHIP-002 | Shipping | Must | Open |
| SUPP-001 | Supplier | Must | Open |
| SUPP-002 | Supplier | Must | Open |

---
*Generated by prompt 6.1 — awaiting XLSX ingest for complete requirement list.*
*Last updated: seed (wave-6)*
