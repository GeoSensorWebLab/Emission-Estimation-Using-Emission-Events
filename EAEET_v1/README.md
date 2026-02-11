# Emission Event Analysis Tool (EAEET) v1

A Dash-based web application for analyzing emission events and estimating total emissions using advanced simulation techniques.

## Features

- **Data Loading**: Upload CSV files with emission measurements
- **Emission Event Conversion**: Automatically convert measurements to emission events using Allen's Interval Algebra
- **Distribution Fitting**: Fit statistical distributions to rate and duration data
- **Duration Uncertainty Analysis**: Estimate duration uncertainty for intermittent emissions
- **Simulation Methods**:
  - Bootstrap simulation for unmeasured emissions
  - Below detection limit (MDL) simulation with multiple technology support
- **Results Visualization**: Compare results with bottom-up inventories

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Navigate to the EAEET_v1 directory:
```bash
cd EAEET_v1
```

2. Run the application:
```bash
python app.py
```

3. Open your web browser and navigate to:
```
http://localhost:8050
```

## Usage Guide

### Step 1: Load Emissions Data
1. Upload your CSV file containing emission measurements
2. Map columns to required fields (ID, Rate, Time, Source)
3. Review converted emission events

### Step 2: Emissions Event Browser
1. View rate and duration distributions
2. Fit statistical distributions to your data
3. Configure emission characteristics (intermittent or continuous)
4. Estimate duration uncertainty if needed

### Step 3: Run Simulations
1. Select estimation approach:
   - **Bootstrap**: For unmeasured emissions extrapolation
   - **Below MDL**: For emissions below detection limit
2. Configure simulation parameters:
   - Start and end dates
   - Number of Monte Carlo iterations
   - Measurement technology
   - Wind considerations (optional)
3. Run simulation

### Step 4: View Results
1. Review total emissions with confidence intervals
2. Compare measured vs unmeasured emissions
3. Compare with bottom-up inventory (optional)

## Data Format

Your CSV file should contain at minimum:
- **ID**: Unique identifier for each measurement
- **Rate**: Emission rate (kg/hr)
- **Time**: Detection/measurement timestamp
- **Source**: Source location or identifier

Optional columns:
- **Cause**: Root cause or mechanism
- **Start Time**: Temporal bound start
- **End Time**: Temporal bound end
- **Uncertainties**: Measurement uncertainties
- **Observation Type**: Type of observation (e.g., "operation")

## Supported Technologies

The tool supports multiple detection technologies:
- InsightM
- Qube
- SeekOps
- Bridger Photonic
- GHGSat-Air
- Kuva Systems
- Sensirion
- Aeromon
- Project Canary
- Long Path
- User Defined (custom MDL)

## Troubleshooting

### Application won't start
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that port 8050 is not in use

### File upload fails
- Ensure your CSV file is properly formatted
- Check that required columns are present
- Verify data types (rates should be numeric)

### Simulation errors
- Verify that start date is before end date
- Ensure emission events overlap with simulation period
- Check that all required parameters are provided

## Technical Details

### Emission Event Conversion
Uses Allen's Interval Algebra to merge overlapping emission events from the same source. Events are classified as:
- **RE (Resolved Events)**: Events with observation_type = "operation"
- **PRE (Partially Resolved Events)**: Events with other observation types

### Simulation Methods

**Bootstrap Simulation**:
- Samples from rate and duration distributions
- Uses probability of emission to simulate unmeasured events
- Supports fitted distributions for improved accuracy

**Below MDL Simulation**:
- Simulates emissions below detection limit
- Supports multiple technologies (emission detected if ANY technology detects)
- Can incorporate wind speed effects
- Uses component-level leak data

### Duration Uncertainty
- Estimates duration using leak production rate and repair rate
- Monte Carlo simulation for uncertainty quantification
- Provides 95% confidence intervals

## Contact

For questions, issues, or commercial licensing:
- Email: mozhou.gao@ucalgary.ca

## License

This software is provided exclusively for academic research and educational purposes.
Unauthorized commercial use, distribution, or modification is prohibited.
