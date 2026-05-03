# Pranali Engineering Systems — Product Portfolio

> Customer: Reliance Industries Ltd (RIL), Module R&D Laboratory
> Geography: India | Version: wave-6 seed

## Overview

Pranali Engineering Systems provides PV module characterisation and reliability
test equipment for the Indian solar manufacturing and R&D sector.

## Product Roadmap

| ID | Product | Technology | Scale | Budget (USD) | Target FAT | Standards |
|----|---------|------------|-------|--------------|------------|-----------|
| **P0** | BBA Steady-State Sun Simulator | MH or LED | 2 modules | 100k–220k | **Nov 2026** | IEC 60904-9:2020 A+A+A+ |
| P1 | DC-PSU TC-HF-LeTID Tester | DC-PSU | 10 channels | TBD | TBD | IEC 62804 |
| P2 | DC-PSU PID Tester | DC-PSU | 10 channels | TBD | TBD | IEC 62804 |
| P3 | Climate Chamber TC/HF/DH | Environmental | 20 modules | TBD | TBD | IEC 60068-2-x |
| P4 | UV Pre-conditioning Chamber | UV | 10 modules | TBD | TBD | IEC 61345 |
| P5 | 4-in-1 TC+HF+DH+UV | Combined | 2 modules | TBD | TBD | IEC 60068-2-x, IEC 61345 |
| P6 | Programmable Electronic Load | E-Load | 100/300V 35A | TBD | TBD | IEC 61010-1 |

## P0 — BBA Steady-State Sun Simulator (Priority Product)

P0 is the first product under development for RIL Module R&D Laboratory.

**Key specifications:**
- IEC 60904-9:2020 Class A+A+A+ (spatial uniformity, temporal instability, spectral match)
- 2 full-size commercial PV modules simultaneously
- Irradiance: 700–1300 W/m²
- Temperature control: 20–75 °C
- 4-wire Kelvin I-V measurement per IEC 60904-1
- ISO/IEC 17025:2017 calibration traceability
- Source technology: Metal-Halide (USD 100k) or LED array (USD 220k)

**URS**: iRIL-MxML-FRM-GE-003-Rev00 → `docs/urs/p0_steady_state_simulator.md`

## P1 — DC-PSU TC-HF-LeTID Tester

10-channel DC power supply system for temperature coefficient (TC),
heat & freeze (HF), and LeTID (Light and elevated Temperature Induced
Degradation) stress testing per IEC 62804.

## P2 — DC-PSU PID Tester

10-channel DC power supply for Potential-Induced Degradation (PID)
stress testing per IEC 62804. Voltage range: 0–1500 V DC.

## P3 — Climate Chamber TC/HF/DH

20-module climate chamber supporting:
- Thermal Cycling (TC): IEC 60068-2-14, IEC 61215-2
- Humidity-Freeze (HF): IEC 60068-2-30
- Damp-Heat (DH): IEC 60068-2-78

## P4 — UV Pre-conditioning Chamber

10-module UV chamber per IEC 61345. Spectral range 280–400 nm,
dose ≥15 kWh/m² UV.

## P5 — 4-in-1 Combined Chamber

2-module combined stress chamber: TC + HF + DH + UV in single enclosure.
Standards: IEC 60068-2-1/-2/-14/-30/-78, IEC 61345.

## P6 — Programmable Electronic Load

Benchtop/rack programmable electronic load:
- Voltage: 100 V or 300 V range
- Current: 35 A
- Modes: CC, CV, CP, CR
- Applications: PSU testing, battery characterisation, DC-DC converter test

---

## Common Standards (All Products)

| Standard | Scope |
|----------|-------|
| IEC 61010-1 | Laboratory electrical safety |
| IEC 60204-1 | Machine electrical safety |
| IEC 60529 | Enclosure IP ratings |
| RoHS 2011/65/EU | Hazardous substances |
| REACH EC 1907/2006 | Chemical registration |
| IS 13947 | Indian switchgear |
| ISO 9001:2015 | Quality management system |

---

*See individual product files in `docs/urs/` for detailed requirements.*
*Prompt workflow: `prompts/6.0_portfolio.md` through `prompts/6.11_gantt.md`*
