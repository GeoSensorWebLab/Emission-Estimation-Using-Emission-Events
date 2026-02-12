"""
Standalone Validation Script for EAEET Simulation Results

This script validates simulation accuracy through statistical methods:
- Bootstrap Stability Test (consistency across runs)
- Sensitivity Analysis (parameter impact)

Usage:
    python validate_simulation.py <emission_events.csv> [options]

Example:
    python validate_simulation.py emission_events.csv --start-date 2025-01-01 --end-date 2025-12-31 --iterations 50

Requirements:
    - pandas, numpy (install via: pip install -r requirements.txt)
    - Emission events CSV with columns: rate, duration
"""

import argparse
import pandas as pd
import numpy as np
import json
import sys

# Import simulation function
from simulations import extrapolation


def bootstrap_stability_test(rate_list, duration_list, prob_dist, start_time, end_time, num_runs=50, num_iterations=1000):
    """
    Test stability by running simulation multiple times.
    Returns: CV%, mean, std, interpretation
    """
    print("\n" + "="*70)
    print("1. BOOTSTRAP STABILITY TEST")
    print("="*70)
    print(f"Running {num_runs} simulations with {num_iterations} iterations each...")
    
    # Prepare distributions
    rate_dist = {"UNKNOWN": rate_list}
    duration_dist = {"UNKNOWN": duration_list}
    
    results = []
    for i in range(num_runs):
        result = extrapolation(
            prob_dist=prob_dist,
            rate_dist=rate_dist,
            duration_dist=duration_dist,
            start_time=start_time,
            end_time=end_time,
            MC=num_iterations
        )
        # Extract total emissions from result
        total_emissions = np.sum(result["UNKNOWN"])
        results.append(total_emissions)
        if (i + 1) % 10 == 0:
            print(f"  Completed {i + 1}/{num_runs} runs...")
    
    results_array = np.array(results)
    mean_val = np.mean(results_array)
    std_val = np.std(results_array)
    cv = (std_val / mean_val * 100) if mean_val > 0 else 0
    
    # Interpretation
    if cv < 10:
        interpretation = "✅ EXCELLENT - Results are highly consistent"
        status = "PASS"
    elif cv < 20:
        interpretation = "⚠️ ACCEPTABLE - Some variation present"
        status = "PASS"
    else:
        interpretation = "❌ POOR - High variation, increase Monte Carlo iterations"
        status = "FAIL"
    
    print(f"\nResults:")
    print(f"  Mean Emissions:     {mean_val:.2f} kg")
    print(f"  Std Deviation:      {std_val:.2f} kg")
    print(f"  Coefficient of Var: {cv:.2f}%")
    print(f"\nInterpretation: {interpretation}")
    print(f"Status: {status}")
    
    return {
        'test': 'Bootstrap Stability',
        'mean_emissions': mean_val,
        'std_emissions': std_val,
        'cv': cv,
        'interpretation': interpretation,
        'status': status
    }


def sensitivity_analysis(rate_list, duration_list, prob_dist, start_time, end_time, num_iterations=1000, perturbation=0.1):
    """
    Test sensitivity to parameter changes.
    Returns: impact of 10% changes to rates, durations, probability
    """
    print("\n" + "="*70)
    print("2. SENSITIVITY ANALYSIS")
    print("="*70)
    print("Testing impact of 10% parameter changes...")
    
    rate_array = np.array(rate_list)
    duration_array = np.array(duration_list)
    
    # Baseline
    rate_dist = {"UNKNOWN": rate_list}
    duration_dist = {"UNKNOWN": duration_list}
    
    baseline_result = extrapolation(
        prob_dist=prob_dist,
        rate_dist=rate_dist,
        duration_dist=duration_dist,
        start_time=start_time,
        end_time=end_time,
        MC=num_iterations
    )
    baseline_emissions = np.sum(baseline_result["UNKNOWN"])
    
    sensitivities = {}
    
    # Test rate sensitivity
    print("  Testing rate sensitivity...")
    perturbed_rate = (rate_array * (1 + perturbation)).tolist()
    perturbed_rate_dist = {"UNKNOWN": perturbed_rate}
    
    rate_result = extrapolation(
        prob_dist=prob_dist,
        rate_dist=perturbed_rate_dist,
        duration_dist=duration_dist,
        start_time=start_time,
        end_time=end_time,
        MC=num_iterations
    )
    rate_emissions = np.sum(rate_result["UNKNOWN"])
    rate_change = (rate_emissions - baseline_emissions) / baseline_emissions * 100
    sensitivities['rate'] = {
        'change': rate_change,
        'interpretation': f'10% increase in rates → {rate_change:.1f}% change in emissions'
    }
    
    # Test duration sensitivity
    print("  Testing duration sensitivity...")
    perturbed_duration = (duration_array * (1 + perturbation)).tolist()
    perturbed_duration_dist = {"UNKNOWN": perturbed_duration}
    
    duration_result = extrapolation(
        prob_dist=prob_dist,
        rate_dist=rate_dist,
        duration_dist=perturbed_duration_dist,
        start_time=start_time,
        end_time=end_time,
        MC=num_iterations
    )
    duration_emissions = np.sum(duration_result["UNKNOWN"])
    duration_change = (duration_emissions - baseline_emissions) / baseline_emissions * 100
    sensitivities['duration'] = {
        'change': duration_change,
        'interpretation': f'10% increase in durations → {duration_change:.1f}% change in emissions'
    }
    
    # Test probability sensitivity
    print("  Testing probability sensitivity...")
    perturbed_prob = {k: min(v * (1 + perturbation), 1.0) for k, v in prob_dist.items()}
    
    prob_result = extrapolation(
        prob_dist=perturbed_prob,
        rate_dist=rate_dist,
        duration_dist=duration_dist,
        start_time=start_time,
        end_time=end_time,
        MC=num_iterations
    )
    prob_emissions = np.sum(prob_result["UNKNOWN"])
    prob_change = (prob_emissions - baseline_emissions) / baseline_emissions * 100
    sensitivities['probability'] = {
        'change': prob_change,
        'interpretation': f'10% increase in probability → {prob_change:.1f}% change in emissions'
    }
    
    print(f"\nResults:")
    print(f"  Baseline Emissions: {baseline_emissions:.2f} kg")
    print(f"  Rate Sensitivity:   {sensitivities['rate']['interpretation']}")
    print(f"  Duration Sensitivity: {sensitivities['duration']['interpretation']}")
    print(f"  Probability Sensitivity: {sensitivities['probability']['interpretation']}")
    
    return {
        'test': 'Sensitivity Analysis',
        'baseline_emissions': baseline_emissions,
        'sensitivities': sensitivities
    }


def run_validation(csv_file, start_date, end_date, num_iterations=50, output_json=None):
    """
    Main validation function - runs all tests and generates report.
    """
    print("\n" + "="*70)
    print("EAEET SIMULATION VALIDATION")
    print("="*70)
    print(f"Input File: {csv_file}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Validation Iterations: {num_iterations}")
    print("="*70)
    
    # Load data
    try:
        df = pd.read_csv(csv_file)
        print(f"\n✓ Loaded {len(df)} emission events")
    except Exception as e:
        print(f"\n❌ Error loading CSV: {e}")
        return 1
    
    # Validate required columns
    required_cols = ['rate', 'duration']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ Missing required columns: {missing_cols}")
        print(f"Available columns: {list(df.columns)}")
        return 1
    
    # Extract arrays
    rate_array = df['rate'].values
    duration_array = df['duration'].values
    
    # Remove any NaN or zero values
    valid_mask = (rate_array > 0) & (duration_array > 0) & ~np.isnan(rate_array) & ~np.isnan(duration_array)
    rate_array = rate_array[valid_mask]
    duration_array = duration_array[valid_mask]
    
    # Convert to lists for extrapolation function
    rate_list = rate_array.tolist()
    duration_list = duration_array.tolist()
    
    print(f"✓ Valid emission events: {len(rate_array)}")
    print(f"  Rate range: {rate_array.min():.4f} to {rate_array.max():.2f} kg/hr")
    print(f"  Duration range: {duration_array.min():.2f} to {duration_array.max():.2f} hours")
    
    # Calculate simulation parameters
    start_datetime = pd.to_datetime(start_date)
    end_datetime = pd.to_datetime(end_date)
    total_hours = (end_datetime - start_datetime).total_seconds() / 3600
    total_event_hours = duration_array.sum()
    poe = min(max(total_event_hours / total_hours, 0.001), 0.999)
    
    print(f"\nSimulation Parameters:")
    print(f"  Total Hours: {total_hours:.1f}")
    print(f"  Event Hours: {total_event_hours:.1f}")
    print(f"  Probability of Emission (POE): {poe:.4f}")
    
    prob_dist = {"UNKNOWN": poe}
    
    # Run validation tests
    results = {}
    
    # Test 1: Bootstrap Stability
    results['stability'] = bootstrap_stability_test(
        rate_list, duration_list, prob_dist, start_datetime, end_datetime,
        num_runs=num_iterations, num_iterations=1000
    )
    
    # Test 2: Sensitivity Analysis
    results['sensitivity'] = sensitivity_analysis(
        rate_list, duration_list, prob_dist, start_datetime, end_datetime,
        num_iterations=1000, perturbation=0.1
    )
    
    # Overall Assessment
    print("\n" + "="*70)
    print("OVERALL ASSESSMENT")
    print("="*70)
    
    # Check if stability test passed
    stability_passed = results['stability']['status'] == 'PASS'
    
    if stability_passed:
        overall = "✅ PASS - Simulation is stable and consistent"
        recommendation = "Results are suitable for use. CV is within acceptable limits."
        exit_status = 0
    else:
        overall = "❌ FAIL - Simulation shows high variation"
        recommendation = "Increase Monte Carlo iterations in your simulation or collect more data."
        exit_status = 1
    
    print(f"Stability Test: {results['stability']['status']}")
    print(f"Assessment: {overall}")
    print(f"\nRecommendation: {recommendation}")
    print("="*70 + "\n")
    
    # Save results to JSON if requested
    if output_json:
        results['overall'] = {
            'stability_passed': stability_passed,
            'assessment': overall,
            'recommendation': recommendation
        }
        
        # Convert numpy types to Python types for JSON serialization
        def convert_types(obj):
            if isinstance(obj, (np.bool_, bool)):
                return bool(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(item) for item in obj]
            return obj
        
        results = convert_types(results)
        
        with open(output_json, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"✓ Results saved to: {output_json}\n")
    
    return exit_status


def main():
    parser = argparse.ArgumentParser(
        description='Validate EAEET simulation results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_simulation.py emission_events.csv --start-date 2025-01-01 --end-date 2025-12-31
  python validate_simulation.py data.csv -s 2025-01-01 -e 2025-12-31 -i 100 -o results.json
        """
    )
    
    parser.add_argument('csv_file', help='Path to emission events CSV file')
    parser.add_argument('-s', '--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('-e', '--end-date', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('-i', '--iterations', type=int, default=50, 
                       help='Number of validation iterations (default: 50)')
    parser.add_argument('-o', '--output', help='Output JSON file for results (optional)')
    
    args = parser.parse_args()
    
    # Run validation
    exit_code = run_validation(
        args.csv_file,
        args.start_date,
        args.end_date,
        args.iterations,
        args.output
    )
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
