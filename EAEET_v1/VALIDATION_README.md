# Validation System for EAEET

## Summary

A standalone command-line validation script for testing the accuracy and reliability of EAEET simulation results.

## Files

### 1. `validate_simulation.py`
**Standalone validation script** - Run from command line to validate your simulation results.

### 2. `VALIDATION_GUIDE.md`
**Complete user guide** - Comprehensive documentation explaining:
- How to use the validation script
- What each test means
- How to interpret results
- Troubleshooting guide
- Best practices

## Quick Start

```bash
# Basic usage
python validate_simulation.py emission_events.csv --start-date 2025-01-01 --end-date 2025-12-31

# With custom iterations
python validate_simulation.py emission_events.csv -s 2025-01-01 -e 2025-12-31 -i 100

# Save results to JSON
python validate_simulation.py emission_events.csv -s 2025-01-01 -e 2025-12-31 -o results.json
```

## What It Does

The script runs 4 validation tests:

1. **Bootstrap Stability Test** - Tests consistency across multiple runs
2. **Cross-Validation Test** - Tests prediction accuracy
3. **Physical Reality Check** - Verifies results are physically plausible
4. **Sensitivity Analysis** - Measures parameter impact

## Output

- **Console**: Formatted results with ✅ ⚠️ ❌ indicators
- **Exit Code**: 0 = passed, 1 = failed
- **JSON** (optional): Detailed results for further analysis

## Requirements

- Python 3.6+
- pandas, numpy, scipy
- Your EAEET simulation modules (simulations.py)

## Documentation

See `VALIDATION_GUIDE.md` for complete documentation including:
- Detailed usage instructions
- Test explanations
- Interpretation guidelines
- Troubleshooting
- Integration examples

## Example Output

```
======================================================================
EAEET SIMULATION VALIDATION
======================================================================
Input File: emission_events.csv
Date Range: 2025-01-01 to 2025-12-31
Validation Iterations: 50
======================================================================

✓ Loaded 150 emission events
✓ Valid emission events: 148

1. BOOTSTRAP STABILITY TEST
======================================================================
Running 50 simulations with 1000 iterations each...
  Completed 10/50 runs...
  ...

Results:
  Mean Emissions:     1234.56 kg
  Std Deviation:      98.76 kg
  Coefficient of Var: 8.0%

Interpretation: ✅ EXCELLENT - Results are highly consistent
Status: PASS

... (3 more tests) ...

======================================================================
OVERALL ASSESSMENT
======================================================================
Score: 3/3
Assessment: ✅ EXCELLENT - Simulation is highly reliable

Recommendation: Results are suitable for reporting with high confidence.
======================================================================
```

## Integration

### Bash Script
```bash
#!/bin/bash
python validate_simulation.py data.csv -s 2025-01-01 -e 2025-12-31
if [ $? -eq 0 ]; then
    echo "Validation passed"
    python generate_report.py
fi
```

### Python Script
```python
import subprocess
result = subprocess.run([
    'python', 'validate_simulation.py',
    'data.csv', '-s', '2025-01-01', '-e', '2025-12-31'
])
if result.returncode == 0:
    print("Validation passed!")
```

## Support

For detailed information, see `VALIDATION_GUIDE.md`.

---

**Version**: 1.0  
**Last Updated**: February 2026
