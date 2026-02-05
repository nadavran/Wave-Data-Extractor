"""
DuPont WAVE PDF Data Extractor
Extracts data from DuPont WAVE engineering PDF reports using text-based anchors.
Resilient to layout changes - does not use hardcoded page numbers.
"""

import pandas as pd
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def _get_fitz():
    """Lazy import of fitz to avoid import-time issues."""
    import fitz
    return fitz


def split_value_unit(text: str) -> tuple:
    """
    Split a value with unit into separate components.
    E.g., "636.8 m³/h" -> ("636.8", "m³/h")
    """
    if not text or text.strip() == '-':
        return (text, '')
    
    text = text.strip()
    
    pattern = r'^([\d,\.]+)\s*(.*)$'
    match = re.match(pattern, text)
    
    if match:
        value = match.group(1).replace(',', '')
        unit = match.group(2).strip()
        return (value, unit)
    
    return (text, '')


def find_section_page(doc, anchor_text: str) -> int:
    """
    Scan all pages to find the page containing the anchor text.
    Returns page index or -1 if not found.
    """
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        text = page.get_text()
        if anchor_text in text:
            logger.info(f"Found '{anchor_text}' on page {page_idx + 1}")
            return page_idx
    
    logger.warning(f"Section header '{anchor_text}' not found in document")
    return -1


def extract_system_overview_table(doc) -> list:
    """
    Extract data from the table containing RO System Overview data.
    Searches for "RO System Overview" anchor and extracts the flow diagram table.
    """
    results = []
    
    page_idx = find_section_page(doc, "RO System Overview")
    if page_idx == -1:
        page_idx = find_section_page(doc, "RO System Flow Diagram")
    
    if page_idx == -1:
        return results
    
    page = doc[page_idx]
    text = page.get_text()
    lines = text.split('\n')
    
    row_mappings = {
        "Raw Feed to RO System": "Raw Feed to RO System",
        "Total Concentrate from Pass 1": "Total Concentrate",
        "Net Product from RO System": "Net Product"
    }
    
    for i, line in enumerate(lines):
        for search_key, mapped_name in row_mappings.items():
            if search_key in line:
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if re.match(r'^[\d,\.]+$', next_line.replace(',', '')):
                        value = next_line.replace(',', '')
                        results.append({
                            'Section': 'RO System Overview',
                            'Parameter': mapped_name,
                            'Value': value,
                            'Unit': 'm³/h'
                        })
                break
    
    return results


def extract_ccro_overview(doc) -> list:
    """
    Extract data from CCRO Overview section.
    Searches for "CCRO Overview" anchor.
    """
    results = []
    
    page_idx = find_section_page(doc, "CCRO Overview")
    if page_idx == -1:
        return results
    
    page = doc[page_idx]
    text = page.get_text()
    
    ccro_fields = {
        'Elements per PV': 'Elements',
        'Length Of PV': 'Elements',
        'CC Recovery': '%',
        'PF Recovery': '%',
        'PF Feed Ratio': '%',
        'CC Concentrate Flow': 'm³/h/pv',
        'PF Concentrate Flow': 'm³/h/pv',
        'CC Net Feed Flow': 'm³/h/pv',
        'PF Feed Flow': 'm³/h/pv',
        'Total Cycles': '',
        'PF Sequence Duration': 'min',
        'CC Sequence Duration': 'min',
        'Complete Cycle Duration': 'min',
        'CC System Volume': 'm³'
    }
    
    lines = text.split('\n')
    found_fields = set()
    
    for i, line in enumerate(lines):
        for field_name, default_unit in ccro_fields.items():
            if field_name in found_fields:
                continue
            if field_name in line:
                unit_match = re.search(r'\(([^)]+)\)', line)
                unit = unit_match.group(1) if unit_match else default_unit
                
                numbers = re.findall(r'([\d,\.]+)', line)
                if numbers:
                    value = numbers[-1].replace(',', '')
                    results.append({
                        'Section': 'CCRO Overview',
                        'Parameter': field_name,
                        'Value': value,
                        'Unit': unit
                    })
                    found_fields.add(field_name)
                else:
                    for j in range(i+1, min(i+5, len(lines))):
                        next_line = lines[j].strip()
                        if re.match(r'^[\d,\.]+$', next_line.replace(',', '')):
                            value = next_line.replace(',', '')
                            results.append({
                                'Section': 'CCRO Overview',
                                'Parameter': field_name,
                                'Value': value,
                                'Unit': unit
                            })
                            found_fields.add(field_name)
                            break
                break
    
    return results


def extract_stage_level_table(doc) -> list:
    """
    Extract data from RO Flow Table (Stage Level).
    Searches for "RO Flow Table (Stage Level)" anchor.
    The table data is spread across multiple lines in the extracted text.
    """
    results = []
    
    page_idx = find_section_page(doc, "RO Flow Table (Stage Level)")
    if page_idx == -1:
        return results
    
    page = doc[page_idx]
    text = page.get_text()
    lines = text.split('\n')
    
    stage_names = ['PF', 'CC1', 'CC']
    header_fields = ['Elements', '#PV', '#Els per PV', 'Feed Flow', 'Recirc Flow', 
                     'Feed Press', 'Boost Press', 'Conc Flow', 'Conc Press', 
                     'Press Drop', 'Perm Flow', 'Avg Flux', 'Perm Press', 'Perm TDS']
    
    units = ['', '', '', 'm³/h', 'm³/h', 'bar', 'bar', 'm³/h', 'bar', 'bar', 'm³/h', 'LMH', 'bar', 'mg/L']
    
    in_table = False
    current_stage = None
    current_values = []
    stage_results = {}
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if 'RO Flow Table (Stage Level)' in line:
            in_table = True
            continue
        
        if not in_table:
            continue
        
        if 'RO Solute' in line or 'Footnotes' in line or 'Design Warnings' in line:
            break
        
        if stripped in stage_names or (stripped == 'CC' and i + 1 < len(lines) and 'Final' in lines[i+1]):
            if current_stage and current_values:
                stage_results[current_stage] = current_values
            
            if stripped == 'CC' and i + 1 < len(lines) and 'Final' in lines[i+1]:
                current_stage = 'CC Final'
            else:
                current_stage = stripped
            current_values = []
            continue
        
        if current_stage and re.match(r'^[\d,\.]+$', stripped.replace(',', '')):
            current_values.append(stripped.replace(',', ''))
    
    if current_stage and current_values:
        stage_results[current_stage] = current_values
    
    key_fields = [
        (0, 'Elements', ''),
        (1, '#PV', ''),
        (2, 'Feed Flow', 'm³/h'),
        (6, 'Conc Flow', 'm³/h'),
        (9, 'Perm Flow', 'm³/h'),
        (10, 'Avg Flux', 'LMH'),
        (4, 'Feed Press', 'bar'),
        (5, 'Boost Press', 'bar'),
        (13, 'Perm TDS', 'mg/L')
    ]
    
    for stage_name, values in stage_results.items():
        for idx, field_name, unit in key_fields:
            if idx < len(values):
                results.append({
                    'Section': 'RO Flow Table (Stage Level)',
                    'Parameter': f'{stage_name} - {field_name}',
                    'Value': values[idx],
                    'Unit': unit
                })
    
    return results


def extract_wave_data(pdf_path: str, output_path: str = None) -> pd.DataFrame:
    """
    Main extraction function. Extracts all target data from WAVE PDF.
    
    Args:
        pdf_path: Path to the WAVE PDF file
        output_path: Path for Excel output (optional)
    
    Returns:
        DataFrame with extracted data
    """
    all_data = []
    
    logger.info(f"Opening PDF: {pdf_path}")
    
    fitz = _get_fitz()
    doc = fitz.open(pdf_path)
    logger.info(f"PDF has {len(doc)} pages")
    
    logger.info("Extracting RO System Overview data...")
    try:
        system_overview_data = extract_system_overview_table(doc)
        all_data.extend(system_overview_data)
        logger.info(f"  Found {len(system_overview_data)} rows")
    except Exception as e:
        logger.warning(f"  Error extracting RO System Overview: {e}")
    
    logger.info("Extracting CCRO Overview data...")
    try:
        ccro_data = extract_ccro_overview(doc)
        all_data.extend(ccro_data)
        logger.info(f"  Found {len(ccro_data)} rows")
    except Exception as e:
        logger.warning(f"  Error extracting CCRO Overview: {e}")
    
    logger.info("Extracting RO Flow Table (Stage Level) data...")
    try:
        stage_data = extract_stage_level_table(doc)
        all_data.extend(stage_data)
        logger.info(f"  Found {len(stage_data)} rows")
    except Exception as e:
        logger.warning(f"  Error extracting Stage Level data: {e}")
    
    doc.close()
    
    df = pd.DataFrame(all_data, columns=['Section', 'Parameter', 'Value', 'Unit'])
    
    if output_path:
        output_path = Path(output_path)
        df.to_excel(output_path, index=False, sheet_name='WAVE Data')
        logger.info(f"Data exported to: {output_path}")
    
    return df


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    if len(sys.argv) < 2:
        pdf_path = "attached_assets/SFC-CCRO-M120-R85.4-20C_r7_Year_6_SR_wave_extract_2_1770317751580.pdf"
    else:
        pdf_path = sys.argv[1]
    
    output_path = "wave_extracted_data.xlsx"
    
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    
    df = extract_wave_data(pdf_path, output_path)
    
    print("\n" + "="*60)
    print("EXTRACTED DATA SUMMARY")
    print("="*60)
    print(df.to_string(index=False))
    print("="*60)
    print(f"\nTotal rows extracted: {len(df)}")
