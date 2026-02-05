# DuPont WAVE PDF Data Extractor

## Overview
A Python script that extracts structured data from DuPont WAVE engineering PDF reports. The script is designed to be resilient to layout changes by using text-based anchors rather than hardcoded page numbers.

## Features
- **Anchor-based extraction**: Dynamically finds sections by searching for header text across all pages
- **Three target sections extracted**:
  1. **RO System Overview**: Raw Feed, Total Concentrate, Net Product flows
  2. **CCRO Overview**: Elements per PV, CC/PF Recovery, Flow rates, Cycle durations
  3. **RO Flow Table (Stage Level)**: Per-stage data for PF, CC1, CC Final
- **Value/Unit separation**: Automatically splits values from units
- **Excel output**: Generates structured Excel file with Section, Parameter, Value, Unit columns
- **Error resilience**: Logs warnings for missing sections without crashing

## Usage
```bash
# Default: uses sample PDF, outputs to wave_extracted_data.xlsx
python wave_extractor.py

# Custom input/output
python wave_extractor.py <input.pdf> <output.xlsx>
```

## Dependencies
- `pymupdf` (fitz): PDF text extraction
- `pandas`: Data manipulation
- `openpyxl`: Excel export

## Project Structure
- `wave_extractor.py` - Main extraction script
- `wave_extracted_data.xlsx` - Output file (generated)
- `attached_assets/` - Sample PDF files
