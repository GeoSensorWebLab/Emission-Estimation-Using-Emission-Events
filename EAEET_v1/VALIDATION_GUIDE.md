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

### 2. Sensitivity Analysis

**Purpose**: Measures impact of parameter changes on results.

**Method**:
- Perturbs rates, durations, and probability by 10%
- Measures resulting change in emissions
- Identifies which parameters have most impact

**Example Output**:
```
2. SENSITIVITY ANALYSIS
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
| 2/2 | ✅ EXCELLENT | All tests passed | Proceed with confidence |
| 0/2 | ❌ POOR | Significant issues | Investigate before using |

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

