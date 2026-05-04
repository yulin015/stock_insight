# Skill: SEC 13F XML Processor

This skill defines the process for converting SEC 13F Primary and Holding XML files into a structured JSON format suitable for stock analysis.

## Trigger
- "Process 13F for [CIK] and [Period]"
- "Convert 13F XMLs at [directory] to JSON"

## Workflow

### 1. File Identification
- Locate the primary XML (e.g., `*_primary.xml`) and the holdings XML (e.g., `*_holding.xml`).

### 2. Execution
Run the following command to process and aggregate the data:
```bash
python skills/scripts/13f_processor.py \
  --primary [path_to_primary] \
  --holding [path_to_holding] \
  --output repository/13f/CIK_[CIK]/[period].json
```

### 3. Logic (Handled by Script)
- **Aggregation**: Consolidates entries with the same `cusip` (summing values and shares).
- **Metadata**: Extracts `submission_type`, `period_of_report`, `signature_date`, and `table_value_total`.
- **Output**: Generates a clean JSON structure for `stock_analysis_lib.py`.

### 4. Summary
After processing, read the JSON output and provide a summary of the top 5 positions to the user.

## Tools
- `run_command`: To execute the processor script.
- `view_file`: To verify the output.
