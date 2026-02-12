# EAEET Simulation Validation Guide

## Overview

This guide explains how to validate the accuracy and reliability of your EAEET simulation results using the standalone validation script.

## What is Validation?

Validation tests whether your simulation results are:
- **Consistent**: Do multiple runs produce similar results?
- **Accurate**: Do predictions match actual observations?
- **Realistic**: Are results physically plausible?
- **Robust**: How sensitive are results to parameter changes?

## Quick Start

### Requirements

```bash
# Install dependencies (if not already installed)
pip install -r requirements.txt
```

### Basic Usage

```bash
python validate_simulation.py emission_events.csv --start-date 2025-01-01 --end-date 2025-12-31
```

### Command-Line Options

```
python validate_simulation.py <csv_file> [options]

Required arguments:
  csv_file              Path to emission events CSV file
  -s, --start-date     Start date (YYYY-MM-DD)
  -e, --end-date       End date (YYYY-MM-DD)

Optional arguments:
  -i, --iterations     Number of validation iterations (default: 50)
  -o, --output         Output JSON file for results (optional)
```

### Examples

```bash
# Basic validation with 50 iterations (default)
python validate_simulation.py emission_events.csv -s 2025-01-01 -e 2025-12-31

# Thorough validation with 100 iterations
python validate_simulation.py emission_events.csv -s 2025-01-01 -e 2025-12-31 -i 100

# Save results to JSON
python validate_simulation.py emission_events.csv -s 2025-01-01 -e 2025-12-31 -o validation_results.json

# Quick validation with 10 iterations
python validate_simulation.py emission_events.csv -s 2025-01-01 -e 2025-12-31 -i 10
```

## Input Data Requirements

### CSV File Format

Your CSV file must contain at minimum:
- `rate`: Emission rate in kg/hr
- `duration`: Duration in hours

Optional columns (for reference):
- `start_time`: Start timestamp
- `end_time`: End timestamp
- `source`: Emission source
- `id`: Event identifier

### Example CSV

```csv
id,rate,duration,start_time,end_time,source
1,10.5,2.5,2025-01-15 10:00:00,2025-01-15 12:30:00,Site A
2,15.2,1.8,2025-02-20 14:00:00,2025-02-20 15:48:00,Site B
3,8.3,3.2,2025-03-10 09:00:00,2025-03-10 12:12:00,Site A
...
```

## Validation Tests Performed

### 1. Bootstrap Stability Test

**Purpose**: Tests if simulation produces consistent results across multiple runs.

**Method**: 
- Runs simulation N times (where N = validation iterations)
- Calculates mean and standard deviation
- Computes Coefficient of Variation (CV)

**Interpretation**:
- ✅ **CV < 10%**: EXCELLENT - Results are highly consistent
- ⚠️ **CV 10-20%**: ACCEPTABLE - Some variation present
- ❌ **CV > 20%**: POOR - High variation, increase Monte Carlo iterations

**Example Output**:
```
1. BOOTSTRAP STABILITY TEST
======================================================================
Running 50 simulations with 1000 iterations each...
  Completed 10/50 runs...
  Completed 20/50 runs...
  ...

Results:
  Mean Emissions:     1234.56 kg
  Std Deviation:      98.76 kg
  Coefficient of Var: 8.0%

Interpretation: ✅ EXCELLENT - Results are highly consistent
Status: PASS
```

**What to do if it fails**:
- Increase Monte Carlo iterations in your simulation
- Check for data quality issues
- Ensure sufficient sample size (>20 events)

---

### 2. Cross-Validation Test

**Purpose**: Evaluates prediction accuracy using k-fold cross-validation.

**Method**:
- Splits data into 5 folds
- For each fold: trains on 4 folds, tests on 1 fold
- Calculates prediction error for each fold
- Reports mean and standard deviation of errors

**Interpretation**:
- ✅ **Error < 20%**: EXCELLENT prediction accuracy
- ⚠️ **Error 20-30%**: GOOD prediction accuracy
- ❌ **Error > 30%**: POOR - Model may not generalize well

**Example Output**:
```
2. CROSS-VALIDATION TEST
======================================================================
Performing 5-fold cross-validation...
  Fold 1/5: Error = 15.2%
  Fold 2/5: Error = 18.3%
  Fold 3/5: Error = 12.7%
  Fold 4/5: Error = 16.9%
  Fold 5/5: Error = 14.1%

Results:
  Mean Prediction Error: 15.4%
  Error Std Dev:         2.1%

Interpretation: ✅ EXCELLENT prediction accuracy
Status: PASS
```

**What to do if it fails**:
- Collect more emission events data
- Ensure data covers full range of operating conditions
- Check for systematic biases in data

---

### 3. Physical Reality Check

**Purpose**: Verifies simulation results are physically plausible.

**Checks Performed**:
1. **Positive Emissions**: Total emissions should be > 0
2. **Within Physical Bounds**: Emissions shouldn't exceed theoretical maximum
3. **Reasonable Mean Rate**: Implied rate should be within 10x of observed mean

**Example Output**:
```
3. PHYSICAL REALITY CHECK
======================================================================
Checks:
  ✅ Total emissions are positive
  ✅ Emissions (1234.56 kg) within max (5000.00 kg)
  ✅ Implied mean rate (0.1234 kg/hr) is reasonable

Status: PASS
```

**What to do if it fails**:
- Review input data for errors
- Check column mappings are correct
- Verify date range matches data coverage
- Investigate any warnings listed

---

### 4. Sensitivity Analysis

**Purpose**: Measures impact of parameter changes on results.

**Method**:
- Perturbs rates, durations, and probability by 10%
- Measures resulting change in emissions
- Identifies which parameters have most impact

**Example Output**:
```
4. SENSITIVITY ANALYSIS
======================================================================
Testing impact of 10% parameter changes...
  Testing rate sensitivity...
  Testing duration sensitivity...
  Testing probability sensitivity...

Results:
  Baseline Emissions: 1234.56 kg
  Rate Sensitivity:   10% increase in rates → 9.8% change in emissions
  Duration Sensitivity: 10% increase in durations → 10.2% change in emissions
  Probability Sensitivity: 10% increase in probability → 5.1% change in emissions
```

**Interpretation**:
- Parameters with high sensitivity (>10% change) need careful measurement
- Parameters with low sensitivity (<5% change) are less critical
- Results should be roughly proportional to parameter changes

---

## Overall Assessment

The script provides an overall assessment score based on all tests:

```
OVERALL ASSESSMENT
======================================================================
Score: 3/3
Assessment: ✅ EXCELLENT - Simulation is highly reliable

Recommendation: Results are suitable for reporting with high confidence.
======================================================================
```

### Assessment Criteria

| Score | Assessment | Meaning | Action |
|-------|-----------|---------|--------|
| 3/3 | ✅ EXCELLENT | All tests passed | Proceed with confidence |
| 2/3 | ⚠️ GOOD | Minor concerns | Review failed tests, proceed |
| 0-1/3 | ❌ POOR | Significant issues | Investigate before using |

### Exit Codes

- **0**: Validation passed (score ≥ 2)
- **1**: Validation failed (score < 2) or error occurred

This allows integration into automated workflows:

```bash
python validate_simulation.py data.csv -s 2025-01-01 -e 2025-12-31
if [ $? -eq 0 ]; then
    echo "Validation passed - proceeding with analysis"
else
    echo "Validation failed - review results"
fi
```

## Output Options

### Console Output

By default, results are printed to console with formatted output including:
- Progress indicators
- Detailed test results
- Color-coded status indicators (✅ ⚠️ ❌)
- Overall assessment and recommendations

### JSON Output

Use `-o` flag to save results to JSON file:

```bash
python validate_simulation.py data.csv -s 2025-01-01 -e 2025-12-31 -o results.json
```

JSON structure:
```json
{
  "stability": {
    "test": "Bootstrap Stability",
    "mean_emissions": 1234.56,
    "std_emissions": 98.76,
    "cv": 8.0,
    "status": "PASS"
  },
  "cross_validation": {
    "test": "Cross-Validation",
    "mean_error": 15.4,
    "std_error": 2.1,
    "status": "PASS"
  },
  "physical_check": {
    "test": "Physical Reality Check",
    "all_passed": true,
    "status": "PASS"
  },
  "sensitivity": {
    "test": "Sensitivity Analysis",
    "baseline_emissions": 1234.56,
    "sensitivities": {...}
  },
  "overall": {
    "score": 3,
    "max_score": 3,
    "assessment": "EXCELLENT",
    "recommendation": "Results are suitable for reporting..."
  }
}
```

## Validation Best Practices

### 1. When to Validate

✅ **Always validate before**:
- Using results in reports
- Making business decisions
- Publishing findings
- Changing simulation parameters

⚠️ **Consider validating after**:
- Collecting new data
- Updating detection technologies
- Observing unexpected results

### 2. Choosing Iteration Counts

| Iterations | Use Case | Time | Thoroughness |
|-----------|----------|------|-------------|
| 10-20 | Quick check | 1-2 min | Low |
| 50 | Standard validation | 3-5 min | Medium ⭐ |
| 100 | Final validation | 5-10 min | High |

**Recommendation**: Use 50 iterations for routine validation.

### 3. Data Requirements

Minimum requirements:
- **10+ emission events**: For basic validation
- **20+ emission events**: For meaningful cross-validation
- **50+ emission events**: For robust validation

Data quality:
- No missing values in rate/duration
- All rates and durations > 0
- Reasonable range (no extreme outliers)
- Representative of operational conditions

### 4. Interpreting Results

#### If All Tests Pass (3/3):
✅ Proceed with confidence
✅ Document validation in reports
✅ Use results for decision making

#### If Some Tests Fail (2/3):
⚠️ Review failed test details
⚠️ Document limitations
⚠️ Consider if acceptable for your use case
⚠️ May still proceed with cautions

#### If Most Tests Fail (0-1/3):
❌ Do not use results
❌ Investigate root causes:
  - Check data quality
  - Increase Monte Carlo iterations
  - Review simulation parameters
  - Consider collecting more data
❌ Re-run validation after corrections

## Troubleshooting

### Problem: High CV (> 20%)

**Symptoms**:
```
Coefficient of Var: 25.3%
Status: FAIL
```

**Possible Causes**:
- Too few Monte Carlo iterations in simulation
- High variability in emission rates/durations
- Small sample size (<20 events)

**Solutions**:
1. Increase Monte Carlo iterations (try 5000-10000)
2. Check for and remove extreme outliers
3. Collect more emission events data
4. Increase validation iterations (`-i 100`)

---

### Problem: High Prediction Error (> 30%)

**Symptoms**:
```
Mean Prediction Error: 35.2%
Status: FAIL
```

**Possible Causes**:
- Insufficient data
- Non-representative data
- Strong temporal patterns not captured

**Solutions**:
1. Collect more emission events (target 50+)
2. Ensure data covers all operating conditions
3. Check for seasonal or operational patterns
4. Consider stratifying by source or conditions

---

### Problem: Failed Physical Checks

**Symptoms**:
```
❌ Emissions exceed theoretical maximum
⚠️ Implied emission rate is unusually high
Status: FAIL
```

**Possible Causes**:
- Data entry errors
- Incorrect units
- Wrong date range
- Incorrect probability of emission

**Solutions**:
1. Review input data for errors
2. Verify units (kg/hr for rates, hours for durations)
3. Check date range matches data coverage
4. Recalculate probability of emission from data

---

### Problem: CSV Loading Error

**Symptoms**:
```
❌ Error loading CSV: ...
```

**Solutions**:
1. Check file path is correct
2. Ensure CSV format is valid
3. Verify required columns exist: `rate`, `duration`
4. Check for special characters in file path

---

### Problem: Insufficient Data Warning

**Symptoms**:
```
⚠️ WARNING: Insufficient data for cross-validation (need 10+ events)
Status: SKIPPED
```

**Solution**:
- Collect more emission events data
- Minimum 10 events for basic validation
- Recommended 20+ events for robust validation

## Integration into Workflows

### Automated Validation

Example bash script:

```bash
#!/bin/bash
# validate_and_process.sh

DATA_FILE="emission_events.csv"
START_DATE="2025-01-01"
END_DATE="2025-12-31"
OUTPUT_FILE="validation_results.json"

echo "Running validation..."
python validate_simulation.py $DATA_FILE \
    -s $START_DATE \
    -e $END_DATE \
    -i 50 \
    -o $OUTPUT_FILE

if [ $? -eq 0 ]; then
    echo "✅ Validation passed - proceeding with report generation"
    python generate_report.py $DATA_FILE
else
    echo "❌ Validation failed - check results in $OUTPUT_FILE"
    exit 1
fi
```

### Python Integration

```python
import subprocess
import json

# Run validation
result = subprocess.run([
    'python', 'validate_simulation.py',
    'emission_events.csv',
    '-s', '2025-01-01',
    '-e', '2025-12-31',
    '-i', '50',
    '-o', 'validation_results.json'
], capture_output=True)

# Check if validation passed
if result.returncode == 0:
    print("Validation passed!")
    
    # Load results
    with open('validation_results.json') as f:
        validation_data = json.load(f)
    
    # Access specific metrics
    cv = validation_data['stability']['cv']
    print(f"Coefficient of Variation: {cv}%")
else:
    print("Validation failed!")
```

## Reporting Validation Results

### Key Information to Include in Reports

1. **Validation Summary**
   ```
   Validation performed on: [Date]
   Data period: [Start] to [End]
   Number of events: [N]
   Validation iterations: [50/100]
   Overall assessment: [EXCELLENT/GOOD/POOR]
   ```

2. **Test Results**
   - Bootstrap Stability: CV = X%, Status = PASS/FAIL
   - Cross-Validation: Error = Y%, Status = PASS/FAIL
   - Physical Checks: All passed? Yes/No
   - Sensitivity Analysis: Key findings

3. **Recommendations**
   - Confidence level (High/Medium/Low)
   - Suitable uses for results
   - Known limitations

### Example Report Section

```
VALIDATION SUMMARY
==================
The simulation results were validated on February 10, 2026 using 
50 validation iterations across 150 emission events from January 1 
to December 31, 2025.

Results:
- Bootstrap Stability: CV = 8.0% (PASS)
- Cross-Validation: Error = 15.4% (PASS)
- Physical Reality Check: All passed (PASS)
- Overall Assessment: EXCELLENT (3/3)

The simulation demonstrates excellent stability and prediction 
accuracy. Results are suitable for emission estimation and 
reporting with high confidence.
```

## FAQ

**Q: How long does validation take?**
A: Typically 3-10 minutes depending on iterations and dataset size.
   - 10 iterations: ~1-2 minutes
   - 50 iterations: ~3-5 minutes
   - 100 iterations: ~5-10 minutes

**Q: Can I validate results from "Simulate Below Detection Limit"?**
A: Not directly with this script. This script validates bootstrap simulations.
   Below MDL simulations require different validation approaches.

**Q: What if I don't have start/end dates in my CSV?**
A: You must specify dates via command line (`-s` and `-e` flags).
   The script uses these to calculate probability of emission.

**Q: How many emission events do I need?**
A: Minimum 10 for basic validation, 20+ recommended, 50+ ideal.

**Q: Can I run validation on a subset of my data?**
A: Yes, create a filtered CSV file with only the events you want to validate.

**Q: What does the exit code mean?**
A: Exit code 0 = validation passed (score ≥2), 1 = failed or error.

**Q: Should I run validation every time?**
A: Yes, especially before reporting results or making decisions.

**Q: Can I customize the validation tests?**
A: Yes, the script is open source. Modify `validate_simulation.py` as needed.

## Support

For issues or questions:
1. Check this guide's troubleshooting section
2. Review error messages carefully
3. Verify data format and requirements
4. Check that all dependencies are installed

## Version History

- **v1.0** (February 2026): Initial release
  - Bootstrap stability test
  - Cross-validation test
  - Physical reality checks
  - Sensitivity analysis
  - JSON output support

---

**Last Updated**: February 2026
**Version**: 1.0
