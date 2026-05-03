"""
Karaveda tax tables for PV test-equipment HSN codes.

Structure
---------
HSN_TABLE : dict[str, dict]
    key   = HSN code (str, 4- or 8-digit)
    value = {
        "description" : str,
        "gst_rate"    : float,   # % (e.g. 18.0)
        "bcd_rate"    : float,   # Basic Customs Duty %
        "sws_rate"    : float,   # Social Welfare Surcharge on BCD %
    }

Both GST slab and customs rates follow the Indian Customs Tariff / GST Schedule
as applicable to PV test-equipment imports (FY 2024-25).
"""

# ---------------------------------------------------------------------------
# HSN table — PV / electrical test-equipment components
# ---------------------------------------------------------------------------
HSN_TABLE: dict[str, dict] = {
    # --- Chapter 90: Optical / measuring / scientific instruments --------
    "9030": {
        "description": "Oscilloscopes, spectrum analysers and instruments for measuring/detecting",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    "90301000": {
        "description": "Instruments for measuring electrical quantities — cathode-ray oscilloscopes",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    "90302000": {
        "description": "Instruments for measuring/detecting ionising radiations",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    "90303100": {
        "description": "Multimeters — without recording device",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    "90303900": {
        "description": "Other instruments for measuring voltage, current, resistance or power",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    "90308900": {
        "description": "Other instruments for measuring/detecting electrical quantities",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    "9031": {
        "description": "Measuring or checking instruments, appliances and machines NES (Chapter 90)",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    "90318000": {
        "description": "Other measuring/checking instruments (incl. IV-curve tracers, EL testers)",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    "90319000": {
        "description": "Parts and accessories for measuring instruments of heading 9031",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    # --- Chapter 85: Electrical machinery / apparatus --------------------
    "8543": {
        "description": "Electrical machines and apparatus with individual functions NES",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    "85437090": {
        "description": "Other electrical machines (incl. sun simulators, flash testers)",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    "8504": {
        "description": "Transformers, static converters and inductors",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    "85044090": {
        "description": "Other static converters (incl. DC power supplies for PV testers)",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    "85044010": {
        "description": "Static converters for telecommunication apparatus",
        "gst_rate": 18.0,
        "bcd_rate": 0.0,
        "sws_rate": 10.0,
    },
    "8539": {
        "description": "Filament or discharge lamps; arc lamps; LED lamps",
        "gst_rate": 12.0,
        "bcd_rate": 10.0,
        "sws_rate": 10.0,
    },
    "85394900": {
        "description": "Other arc lamps (incl. xenon short-arc for sun simulators)",
        "gst_rate": 12.0,
        "bcd_rate": 10.0,
        "sws_rate": 10.0,
    },
    "8471": {
        "description": "Automatic data-processing machines and units thereof",
        "gst_rate": 18.0,
        "bcd_rate": 0.0,
        "sws_rate": 10.0,
    },
    "84713010": {
        "description": "Laptops / portable ADP machines (control PCs for test stations)",
        "gst_rate": 18.0,
        "bcd_rate": 0.0,
        "sws_rate": 10.0,
    },
    "8544": {
        "description": "Insulated wire, cable and other insulated electric conductors",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    "85444290": {
        "description": "Other electric conductors, fitted with connectors, voltage <= 1000 V",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    "8486": {
        "description": "Machines for manufacture of semiconductor devices / electronic ICs",
        "gst_rate": 18.0,
        "bcd_rate": 0.0,
        "sws_rate": 10.0,
    },
    "84869000": {
        "description": "Parts/accessories of semiconductor manufacturing machines",
        "gst_rate": 18.0,
        "bcd_rate": 0.0,
        "sws_rate": 10.0,
    },
    # --- Chapter 70: Glass products ------------------------------------
    "7020": {
        "description": "Other articles of glass (incl. optical glass blanks, integrating spheres)",
        "gst_rate": 18.0,
        "bcd_rate": 10.0,
        "sws_rate": 10.0,
    },
    "70200090": {
        "description": "Other glass articles (optical / laboratory use)",
        "gst_rate": 18.0,
        "bcd_rate": 10.0,
        "sws_rate": 10.0,
    },
    # --- Chapter 39: Plastics -----------------------------------------
    "3926": {
        "description": "Other articles of plastics",
        "gst_rate": 18.0,
        "bcd_rate": 10.0,
        "sws_rate": 10.0,
    },
    "39269099": {
        "description": "Other plastic articles NES (enclosures, connectors, standoffs)",
        "gst_rate": 18.0,
        "bcd_rate": 10.0,
        "sws_rate": 10.0,
    },
    # --- Chapter 73: Articles of iron or steel ------------------------
    "7326": {
        "description": "Other articles of iron or steel (frames, brackets)",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
    "73269099": {
        "description": "Other iron/steel articles NES (structural parts for test rigs)",
        "gst_rate": 18.0,
        "bcd_rate": 7.5,
        "sws_rate": 10.0,
    },
}


def lookup(hsn_code: str) -> dict:
    """Return tax-table entry for an HSN code (exact or 4-digit parent).

    Raises KeyError if neither the code nor its 4-digit prefix is found.
    """
    code = hsn_code.strip().replace(" ", "").replace(".", "")
    if code in HSN_TABLE:
        return {"hsn_code": code, **HSN_TABLE[code]}
    # Fall back to 4-digit heading
    prefix = code[:4]
    if prefix in HSN_TABLE:
        return {"hsn_code": prefix, **HSN_TABLE[prefix]}
    raise KeyError(f"HSN code not found in karaveda tax tables: {hsn_code!r}")
