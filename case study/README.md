# Case Studies: Emission Estimation Using Emission Events

This directory contains case studies demonstrating the process of estimating emissions using emission events. The case studies showcase different approaches to converting emission observations into emission events and estimating total emissions with uncertainty quantification.

More details about this study can be found in Gao et al., 2025.

## Overview

The case studies demonstrate:
- Conversion of emission observations to emission events
- Temporal and spatial event merging using Allen's Interval Algebra
- Uncertainty quantification for resolved (RE), partially resolved (PRE), and unresolved (UE) events
- Comparison with bottom-up inventories (Global Fuel Exploitation Inventory - GFEI)
- Integration of Carbon Mapper satellite data

## Directory Structure

```
case study/
├── Notebooks/
│   ├── Case_study_No1.ipynb                    # Case Study 1: Carbon Mapper data analysis
│   ├── Results_compare_for_case_study_No1.ipynb # Case Study 1: Results comparison with GFEI
│   └── Results_for_case_study_No2.ipynb        # Case Study 2: Results visualization
├── Input Data/
│   ├── Synthetic_multiscale_emissions_observations.csv  # Synthetic emission observations
│   ├── CM_sources.json                         # Carbon Mapper sources (GeoJSON)
│   ├── CM_plumes.csv                           # Carbon Mapper plume detections
│   ├── CM_emission_events.csv                  # Carbon Mapper emission events
│   ├── sample_leak_rate.csv                    # Component-level leak rates
│   ├── weather_permian.nc                      # Weather data (NetCDF format)
│   ├── Global_Fuel_Exploitation_Inventory_v3_2020_Total_Fuel_Exploitation.nc  # GFEI inventory
│   ├── Global_Fuel_Exploitation_Inventory_Total_Fuel_Exploitation_gsd.nc      # GFEI gridded data
│   ├── Global_Fuel_Exploitation_Inventory_Total_Fuel_Exploitation_rsd.nc     # GFEI regional data
│   └── shapefiles/                             # Geographic boundary files
│       ├── Boundary_PermianBasin_StudyArea_NAD27.*  # Permian Basin study area
│       └── Boundary_State_NAD27.*              # State boundaries
└── Output Data/
    ├── emission_events_case_study_2.csv        # Emission events for Case Study 2
    └── total_emissions.csv                     # Total emissions estimates with uncertainties

```

## Case Study 1: Carbon Mapper Satellite Data Analysis

### Description
This case study demonstrates the analysis of real-world satellite data from Carbon Mapper, converting plume detections into emission events and comparing results with the Global Fuel Exploitation Inventory (GFEI).

### Notebooks

#### `Case_study_No1.ipynb`
- **Purpose**: Processes Carbon Mapper satellite data to create emission observations and events
- **Key Steps**:
  1. Loads Carbon Mapper sources and plumes from JSON and CSV files
  2. Joins plume and source data to create emission observations
  3. Converts observations to emission events
  4. Analyzes event characteristics (rates, durations, uncertainties)
- **Input Files**:
  - `CM_sources.json` - Carbon Mapper source locations and metadata
  - `CM_plumes.csv` - Carbon Mapper plume detection data
  - `CM_emission_events.csv` - Pre-processed emission events
- **Output**: Emission events with resolved (RE) and partially resolved (PRE) classifications

#### `Results_compare_for_case_study_No1.ipynb`
- **Purpose**: Compares emission estimates with bottom-up inventory (GFEI)
- **Key Steps**:
  1. Loads emission event results from Case Study 1
  2. Loads Global Fuel Exploitation Inventory (GFEI) data
  3. Processes geographic boundaries (Permian Basin study area)
  4. Creates spatial comparisons and visualizations
  5. Generates comparison plots between top-down (event-based) and bottom-up (inventory) estimates
- **Input Files**:
  - `CM_emission_events.csv` - Emission events from Case Study 1
  - `Global_Fuel_Exploitation_Inventory_v3_2020_Total_Fuel_Exploitation.nc` - GFEI inventory
  - `shapefiles/Boundary_PermianBasin_StudyArea_NAD27.shp` - Study area boundary
  - `shapefiles/Boundary_State_NAD27.shp` - State boundaries
- **Output**: Comparison visualizations and analysis

### Input Data Files

#### Carbon Mapper Data
- **`CM_sources.json`**: GeoJSON file containing Carbon Mapper source locations with properties:
  - Source coordinates (latitude, longitude)
  - Plume IDs and counts
  - Observation scene names
  - Persistence metrics
  - Emission rates and uncertainties
  - Timestamp ranges

- **`CM_plumes.csv`**: CSV file containing individual plume detections with:
  - Plume IDs
  - Emission rates (`emission_auto`)
  - Emission uncertainties (`emission_uncertainty_auto`)
  - Detection timestamps

- **`CM_emission_events.csv`**: Pre-processed emission events derived from Carbon Mapper data

#### Global Fuel Exploitation Inventory (GFEI)
- **`Global_Fuel_Exploitation_Inventory_v3_2020_Total_Fuel_Exploitation.nc`**: Main GFEI inventory file
  - Annual methane emissions from total fuel exploitation
  - Units: Mg a⁻¹ km⁻² (converted to kg a⁻¹ in analysis)
  - Spatial resolution: 0.1° × 0.1°
  - Coverage: Global

- **`Global_Fuel_Exploitation_Inventory_Total_Fuel_Exploitation_gsd.nc`**: Gridded spatial distribution

- **`Global_Fuel_Exploitation_Inventory_Total_Fuel_Exploitation_rsd.nc`**: Regional spatial distribution

#### Geographic Data
- **`shapefiles/`**: Contains shapefiles for geographic boundaries
  - `Boundary_PermianBasin_StudyArea_NAD27.*` - Permian Basin study area boundary
  - `Boundary_State_NAD27.*` - State boundaries (NAD27 coordinate system)

## Case Study 2: Synthetic Multi-Scale Observations

### Description
This case study demonstrates the emission event framework using synthetic multi-scale emission observations, including different measurement technologies and temporal resolutions.

### Notebooks

#### `Results_for_case_study_No2.ipynb`
- **Purpose**: Visualizes and analyzes results from Case Study 2
- **Key Steps**:
  1. Loads emission events from Case Study 2
  2. Separates resolved events (RE) and partially resolved events (PRE)
  3. Creates scatter plots of rates vs. durations with error bars
  4. Analyzes event characteristics and uncertainties
- **Input Files**:
  - `emission_events_case_study_2.csv` - Emission events with classifications
- **Output**: Visualization plots (e.g., `event_rates_scatter.png`)

### Input Data Files

- **`Synthetic_multiscale_emissions_observations.csv`**: Synthetic emission observations with:
  - Observation IDs
  - Site IDs
  - Observation times and time ranges (startTime, endTime)
  - Emission rates (kg/hr)
  - Measurement technology (e.g., CMS - Continuous Monitoring System)
  - Uncertainty values

### Output Data Files

- **`emission_events_case_study_2.csv`**: Emission events converted from observations with:
  - Event IDs (UUIDs)
  - Rates, durations, and quantities
  - Source locations
  - Start and end times
  - Merged observation IDs
  - Event types (RE, PRE, UE)
  - Uncertainty values

- **`total_emissions.csv`**: Aggregated emission estimates with:
  - Source identifiers
  - Partially resolved event emissions (PRE) with uncertainty bounds
  - Unresolved event emissions (UE) with uncertainty bounds
  - Total emissions with lower and upper bounds

## Shared Data Files

### Component-Level Leak Data
- **`sample_leak_rate.csv`**: Component-level leak rates from datasets organized by Rutherford et al., 2021
  - Used for simulating emissions below detection limits
  - Contains leak rates in g/s (converted to kg/hr in analysis)
  - Used in "Simulate Below Detection Limit" approach

### Weather Data
- **`weather_permian.nc`**: Weather data for Permian Basin downloaded from ERA5
  - NetCDF format
  - Contains wind speed components (u10, v10)
  - Used for wind-aware probability of detection calculations
  - Required for technology-specific POD/MDL functions that consider wind conditions

## Event Classifications

The case studies classify emission events into three categories:

1. **Resolved Events (RE)**: Events with both rate and duration fully observed
   - Complete temporal and quantitative information
   - Lower uncertainty compared to PRE and UE

2. **Partially Resolved Events (PRE)**: Events with rate observed but duration uncertain
   - Rate information available
   - Duration estimated using Leak Production Rate (LPR) and Non-Repair Rate (NRR)
   - Moderate uncertainty

3. **Unresolved Events (UE)**: Events not directly observed
   - Estimated using bootstrap methods or component-level leak data
   - Highest uncertainty
   - Critical for comprehensive emission inventories

## Dependencies

The notebooks require the following Python packages (see `../EAEET_v1/requirements.txt`):
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `scipy` - Statistical distributions
- `matplotlib` - Plotting
- `netCDF4` - NetCDF file reading
- `cartopy` - Geographic projections and mapping
- `geopandas` - Geographic data processing
- `xarray` - Multi-dimensional arrays
- `rasterio` - Geospatial raster I/O
- `shapely` - Geometric operations

Additionally, the notebooks import modules from the main EAEET application:
- `simulations` - Simulation functions
- `utils` - Utility functions
- `emission_event_converter` - Event conversion logic

## Usage

1. **Navigate to the case study directory**:
   ```bash
   cd "case study"
   ```

2. **Ensure dependencies are installed**:
   ```bash
   cd ../EAEET_v1
   pip install -r requirements.txt
   ```

3. **Run notebooks in order**:
   - For Case Study 1: Start with `Case_study_No1.ipynb`, then `Results_compare_for_case_study_No1.ipynb`
   - For Case Study 2: Use `Results_for_case_study_No2.ipynb` (assumes events have been created)

4. **Note**: Some notebooks may reference data files that need to be generated by previous steps or the main EAEET application.

## Key Results

The case studies demonstrate:
- Successful conversion of multi-scale observations to emission events
- Temporal merging using Allen's Interval Algebra
- Uncertainty quantification across event types
- Comparison with bottom-up inventories (GFEI)
- Integration of satellite data (Carbon Mapper) with ground-based observations

## Citation

If you use these case studies in your research, please cite:

Gao et al., 2025 (DOI to be added)

## References

- Rutherford et al., 2021 - Component-level leak rate datasets
- Carbon Mapper - Satellite methane detection data
- Global Fuel Exploitation Inventory (GFEI) - Bottom-up emission inventory
- ERA5 - Weather reanalysis data
