# URS Source Documents

**⚠️ CONFIDENTIAL — Do not commit XLSX files to this repository.**

## Purpose
This directory holds the original RIL URS spreadsheets used as input to
prompt `6.1_urs.md` (URS ingest workflow).

## Files expected here (gitignored)

| File | Description |
|------|-------------|
| `iRIL-MxML-FRM-GE-003-Rev00.xlsx` | RIL P0 Sun Simulator URS (master) |
| `*.xlsx` | Any subsequent URS revisions |

## Instructions
1. Obtain the URS XLSX from the RIL project coordinator.
2. Place it in this directory.
3. Run prompt `6.1_urs.md` to ingest and convert to markdown.
4. The XLSX remains here but is excluded from git (see `.gitignore`).

## Security
- These files contain customer-confidential requirements.
- Do not email, share, or upload to any public service.
- Access restricted to project team members under NDA.
