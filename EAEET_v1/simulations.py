"""
Simulation functions for emission estimation.

This module contains all simulation-related functions:
- extrapolation: Bootstrap simulation for unmeasured emissions
- simulate_below_mdl: Simulation for emissions below detection limit
- simulate_duration_uncertainty: Duration uncertainty simulation
"""

import numpy as np
import pandas as pd
import os
from multiprocessing import Pool, cpu_count
from utils import probability_of_detection
from scipy.stats import lognorm, norm, uniform, expon, weibull_min, gamma

# Load leak rate data (used by simulate_below_mdl)
_leak_rates = None
_leaks_dist = None
_num_comps = None

def _load_leak_data(leak_data=None):
    """Load leak rate data from CSV file (lazy loading) or use provided leak data
    
    Args:
        leak_data: Optional list of leak rate values (in kg/hr). If provided, uses this instead of loading from file.
    """
    global _leak_rates, _leaks_dist, _num_comps
    
    if _leaks_dist is None or leak_data is not None:
        if leak_data is not None:
            # Use user-provided leak data
            # Convert to numpy array and ensure values are positive
            leaks_array = np.array(leak_data, dtype=float)
            # Replace zeros or negative values with 0.0001
            _leaks_dist = np.where(leaks_array <= 0, 0.0001, leaks_array)
            _leak_rates = None  # Not needed when using user data
        else:
            # Load from default CSV file
            # Get the directory where this file is located
            current_dir = os.path.dirname(os.path.abspath(__file__))
            csv_path = os.path.join(current_dir, "sample_leak_rate.csv")
            
            if os.path.exists(csv_path):
                _leak_rates = pd.read_csv(csv_path)
                # Use numpy array operations for better performance
                leaks_array = _leak_rates["gpersec"].values
                # Replace zeros with 0.0001 using numpy where
                _leaks_dist = np.where(leaks_array == 0, 0.0001, leaks_array)
            else:
                raise FileNotFoundError(f"Default leak data file not found: {csv_path}")
        
        # Component distribution - use rejection sampling more efficiently
        # (only generate if not already set, or if using new leak data)
        if _num_comps is None or leak_data is not None:
            mean = 2720  # Centered within the range of 1 and 5440
            std_dev = 800  # Adjust for desired spread
            
            # Generate samples more efficiently using numpy
            # Generate more samples than needed to account for rejection
            samples_needed = 10000
            # Generate ~1.5x samples to account for rejection (empirical)
            samples_to_generate = int(samples_needed * 1.5)
            samples = np.random.normal(mean, std_dev, samples_to_generate)
            # Filter and clip to valid range
            valid_samples = samples[(samples >= 1) & (samples <= 5440)]
            # If we don't have enough, generate more
            while len(valid_samples) < samples_needed:
                additional = np.random.normal(mean, std_dev, samples_needed)
                valid_samples = np.concatenate([valid_samples, additional[(additional >= 1) & (additional <= 5440)]])
            _num_comps = valid_samples[:samples_needed].astype(int)


def _extrapolation_continuous_single_iteration(args):
    """
    Helper function for parallel processing - simulates a single continuous emission iteration.
    For continuous emissions with producing hours: sample rates only, calculate avg_rate × producing_hours.
    This function must be at module level for pickling in multiprocessing.
    """
    (rate_array, producing_hours, seed) = args
    
    # Set random seed for reproducibility
    np.random.seed(seed)
    
    # Sample rates (sample multiple times to get average)
    num_samples = 1000  # Sample 1000 rates to get a good average
    sampled_rates = np.random.choice(rate_array, size=num_samples)
    
    # Calculate average rate
    avg_rate = np.mean(sampled_rates)
    
    # Finalized unmeasured emissions = average rate × producing hours
    total_emissions = avg_rate * producing_hours
    
    return total_emissions


def extrapolation(prob_dist, rate_dist, duration_dist, start_time, end_time, MC, 
                  fitted_rate_dist=None, fitted_duration_dist=None,
                  is_continuous=False, producing_hours=None):
    """
    Bootstrap simulation for unmeasured emissions (extrapolation).
    
    Args:
        prob_dist: Probability distribution dictionary
        rate_dist: Rate distribution dictionary (used if fitted_rate_dist is None)
        duration_dist: Duration distribution dictionary (used if fitted_duration_dist is None)
        start_time: Start datetime for simulation
        end_time: End datetime for simulation
        MC: Number of Monte Carlo iterations
        fitted_rate_dist: Optional fitted distribution info for rate (dict with 'type', 'params', etc.)
        fitted_duration_dist: Optional fitted distribution info for duration (dict with 'type', 'params', etc.)
        is_continuous: If True, emissions are continuous (don't sample duration)
        producing_hours: Producing hours for continuous emissions (required if is_continuous=True)
    
    Returns:
        Dictionary with extrapolated emissions by source category
    """
    # only 1 source category
    final_emissions = {"UNKNOWN": []}
    
    # Use fitted distributions if available, otherwise use raw data arrays
    if fitted_rate_dist is not None:
        # Generate samples from fitted distribution
        rate_array = sample_from_distribution(fitted_rate_dist, size=10000)
    else:
        # Convert distributions to numpy arrays for faster access
        rate_array = np.array(rate_dist["UNKNOWN"])
    
    # Handle continuous emissions case
    if is_continuous and producing_hours is not None:
        # For continuous emissions: sample rates only, use avg_rate × producing_hours
        # Use parallel processing for high MC iterations (threshold: 20)
        PARALLEL_THRESHOLD = 20
        use_parallel = MC >= PARALLEL_THRESHOLD
        
        if use_parallel:
            # Prepare arguments for parallel processing
            seeds = np.random.randint(0, 2**31, size=MC)
            args_list = [
                (rate_array, producing_hours, int(seed))
                for seed in seeds
            ]
            
            # Use multiprocessing Pool
            num_workers = min(cpu_count(), MC)
            with Pool(processes=num_workers) as pool:
                results = pool.map(_extrapolation_continuous_single_iteration, args_list)
            final_emissions["UNKNOWN"] = results
        else:
            # Sequential processing for small iterations
            for mc in range(MC):
                # Sample rates (sample multiple times to get average)
                num_samples = 1000  # Sample 1000 rates to get a good average
                sampled_rates = np.random.choice(rate_array, size=num_samples)
                
                # Calculate average rate
                avg_rate = np.mean(sampled_rates)
                
                # Finalized unmeasured emissions = average rate × producing hours
                total_emissions = avg_rate * producing_hours
                final_emissions["UNKNOWN"].append(total_emissions)
        
        return final_emissions
    
    # Original intermittent emissions logic
    poe = prob_dist.get("UNKNOWN")
    
    if fitted_duration_dist is not None:
        # Generate samples from fitted distribution
        duration_array = sample_from_distribution(fitted_duration_dist, size=10000)
    else:
        # Convert distributions to numpy arrays for faster access
        duration_array = np.array(duration_dist["UNKNOWN"])
    
    # Pre-calculate total simulation hours
    total_hours = int((end_time - start_time).total_seconds() / 3600)
    
    # Use parallel processing for high MC iterations (threshold: 20)
    PARALLEL_THRESHOLD = 20
    use_parallel = MC >= PARALLEL_THRESHOLD
    
    if use_parallel:
        # Prepare arguments for parallel processing
        seeds = np.random.randint(0, 2**31, size=MC)
        args_list = [
            (total_hours, poe, rate_array, duration_array, int(seed))
            for seed in seeds
        ]
        
        # Use multiprocessing Pool
        num_workers = min(cpu_count(), MC)
        with Pool(processes=num_workers) as pool:
            results = pool.map(_extrapolation_single_iteration, args_list)
        final_emissions["UNKNOWN"] = results
    else:
        # Sequential processing for small iterations
        for mc in range(MC):
            # start of the simulation 
            extrapolated_emissions = []
            
            # Use hours since start for faster comparison
            sim_hours = 0
            
            while sim_hours < total_hours:   
                # Sample a 1 or 0 based on the probabilities
                sample = np.random.binomial(1, poe)
                if sample == 0: 
                    sim_hours += 1
                else:
                    random_rate = np.random.choice(rate_array)
                    random_duration = np.random.choice(duration_array)
                    
                    # Check if duration exceeds remaining time
                    remaining_hours = total_hours - sim_hours
                    if random_duration > remaining_hours:
                        random_duration = remaining_hours

                    extrapolated_emissions.append(random_duration * random_rate)
                    sim_hours += random_duration
                    
            # finalize simulation results using numpy sum (faster)
            final_emissions["UNKNOWN"].append(np.sum(extrapolated_emissions) if extrapolated_emissions else 0)

    return final_emissions


def sample_from_distribution(distribution_info, size=1):
    """
    Sample values from a fitted statistical distribution.
    
    Args:
        distribution_info: Dictionary with keys:
            - 'type': Distribution type ('lognormal', 'normal', 'uniform', 'exponential', 'weibull', 'gamma')
            - 'params': Distribution parameters (tuple or list)
            - 'min': Minimum value (optional, for clipping)
            - 'max': Maximum value (optional, for clipping)
        size: Number of samples to generate
    
    Returns:
        Array of sampled values
    """
    if distribution_info is None:
        raise ValueError("Distribution info is required")
    
    dist_type = distribution_info.get('type')
    params = distribution_info.get('params')
    
    if params is None:
        raise ValueError("Distribution parameters are required")
    
    # Convert params to tuple if it's a list
    if isinstance(params, list):
        params = tuple(params)
    
    # Sample from distribution
    if dist_type == 'lognormal':
        samples = lognorm.rvs(*params, size=size)
    elif dist_type == 'normal':
        samples = norm.rvs(*params, size=size)
    elif dist_type == 'uniform':
        samples = uniform.rvs(*params, size=size)
    elif dist_type == 'exponential':
        samples = expon.rvs(*params, size=size)
    elif dist_type == 'weibull':
        samples = weibull_min.rvs(*params, size=size)
    elif dist_type == 'gamma':
        samples = gamma.rvs(*params, size=size)
    else:
        raise ValueError(f"Unknown distribution type: {dist_type}")
    
    # Clip to min/max if provided
    if 'min' in distribution_info:
        samples = np.maximum(samples, distribution_info['min'])
    if 'max' in distribution_info:
        samples = np.minimum(samples, distribution_info['max'])
    
    return samples


def _simulate_below_mdl_single_iteration(args):
    """
    Helper function for parallel processing - simulates a single Monte Carlo iteration.
    This function must be at module level for pickling in multiprocessing.
    
    Supports multiple technologies: an emission is detected if ANY technology detects it.
    """
    (total_simulated_time_steps, durations_dist, leaks_dist, num_comps, 
     pod_config_or_list, wind_speed) = args
    
    # Handle both PODs_list (for sequential) and technologies_config (for parallel)
    if isinstance(pod_config_or_list, list) and len(pod_config_or_list) > 0:
        if isinstance(pod_config_or_list[0], dict):
            # It's a technologies_config list - recreate POD functions
            PODs_list = []
            for tech_config in pod_config_or_list:
                POD, _ = probability_of_detection(
                    technology=tech_config['technology'],
                    wind_speed=wind_speed,
                    wind_consider=tech_config['consider_wind'],
                    mdl_define=tech_config.get('mdl_define')
                )
                PODs_list.append(POD)
        else:
            # It's already a PODs_list (for sequential processing)
            PODs_list = pod_config_or_list
    else:
        PODs_list = []
    
    # Set random seed for reproducibility in parallel execution
    np.random.seed(40)
    
    E_miss = 0 
    current_hour = 0
    while current_hour < total_simulated_time_steps:
        detection_label = False
        Q_sample = np.random.choice(leaks_dist) * np.random.choice(num_comps)
            
        # Check detection for each technology
        # An emission is detected if ANY technology detects it
        for POD_func_or_const in PODs_list:
            # Calculate POD based on whether it's a function or constant
            if callable(POD_func_or_const):
                # POD is a function of Q_sample (and possibly wind_speed)
                POD = POD_func_or_const(Q_sample)
            else:
                # POD is a constant
                POD = POD_func_or_const
        
            detection_probs = np.random.random()
            if np.any(POD > detection_probs):
                detection_label = True
                break  # If any technology detects, we can stop checking others
        
        if not detection_label:
            sampled_duration = np.random.choice(durations_dist)
            sampled_duration = min(sampled_duration, total_simulated_time_steps - current_hour)
            E_miss += Q_sample * sampled_duration
            # update time with sampled duration 
            current_hour += sampled_duration
        else: 
            # update time by adding 1 hour 
            current_hour += 1
                
    return E_miss


def _simulate_duration_uncertainty_single_iteration(args):
    """
    Helper function for parallel processing - simulates a single duration uncertainty iteration.
    This function must be at module level for pickling in multiprocessing.
    """
    (total_hours, leak_production_rate, NRR, duration, seed) = args
    
    # Set random seed for reproducibility
    np.random.seed(seed)
    
    sim_hour = 0
    simulated_start_hour = None 
    simulated_end_hour = None 
    
    while sim_hour < total_hours: 
        if simulated_start_hour is None:
            # Check for leak generation
            sample_leak = np.random.binomial(1, leak_production_rate)
            if sample_leak == 1: 
                simulated_start_hour = sim_hour
            sim_hour += 1
        else:
            # Check for repair
            sample_repair = np.random.binomial(1, NRR)
            if sample_repair == 1:
                simulated_end_hour = sim_hour
                break 
            sim_hour += 1

    if simulated_start_hour is None and simulated_end_hour is None:
        sim_duration = duration
    elif simulated_start_hour is not None and simulated_end_hour is None:
        sim_duration = total_hours - simulated_start_hour
    else:
        sim_duration = simulated_end_hour - simulated_start_hour
        
    return sim_duration


def _extrapolation_single_iteration(args):
    """
    Helper function for parallel processing - simulates a single extrapolation iteration.
    This function must be at module level for pickling in multiprocessing.
    """
    (total_hours, poe, rate_array, duration_array, seed) = args
    
    # Set random seed for reproducibility
    np.random.seed(seed)
    
    extrapolated_emissions = []
    sim_hours = 0
    
    while sim_hours < total_hours:   
        # Sample a 1 or 0 based on the probabilities
        sample = np.random.binomial(1, poe)
        if sample == 0: 
            sim_hours += 1
        else:
            random_rate = np.random.choice(rate_array)
            random_duration = np.random.choice(duration_array)
            
            # Check if duration exceeds remaining time
            remaining_hours = total_hours - sim_hours
            if random_duration > remaining_hours:
                random_duration = remaining_hours

            extrapolated_emissions.append(random_duration * random_rate)
            sim_hours += random_duration
            
    return np.sum(extrapolated_emissions) if extrapolated_emissions else 0


def _get_pod_mdl_config(technology, mdl_define, consider_wind, wind_speed):
    """
    Get POD (Probability of Detection) and MDL (Minimum Detection Limit) configuration.
    
    Args:
        technology: Measurement technology name (single technology)
        mdl_define: User-defined MDL value (if technology is 'define_technology')
        consider_wind: Whether to consider wind conditions
        wind_speed: Wind speed value (required when consider_wind=True)
    
    Returns:
        Tuple of (POD, MDL) where POD can be a function or constant
    """
    # Handle technology name mapping
    tech_name = technology
    if technology == "define_technology":
        tech_name = "User Defined"
    
    try:
        POD, MDL = probability_of_detection(
            technology=tech_name,
            wind_speed=wind_speed,
            wind_consider=consider_wind,
            mdl_define=mdl_define
        )
    except ValueError as e:
        raise ValueError(f"Error getting POD/MDL for technology '{technology}': {str(e)}")
    
    return POD, MDL

def calculate_total_simulation_time_steps(event_df, start_time, end_time):
    """
    Calculate total simulation time steps (in hours) from emission event dataframe.
    
    This function sums up the duration of all emission events that overlap with the
    user-defined simulation time period. Events that start before start_time are clipped
    to start_time, and events that end after end_time are clipped to end_time.
    
    Args:
        event_df: DataFrame with emission events. Must have columns for start time and end time.
                 Supports both 'startTime'/'endTime' (camelCase) and 'start_time'/'end_time' (snake_case).
        start_time: User-defined start datetime for the simulation
        end_time: User-defined end datetime for the simulation
    
    Returns:
        Total simulated time steps in hours (float)
    """
    event_df = event_df.copy()
    total_hours = int((end_time - start_time).total_seconds() / 3600)
    
    # Handle both column name formats
    start_col = None
    end_col = None
    
    if 'startTime' in event_df.columns:
        start_col = 'startTime'
        end_col = 'endTime'
    elif 'start_time' in event_df.columns:
        start_col = 'start_time'
        end_col = 'end_time'
    else:
        raise ValueError("Event DataFrame must have 'startTime'/'endTime' or 'start_time'/'end_time' columns")
    
    # Convert to datetime
    event_df[start_col] = pd.to_datetime(event_df[start_col])
    event_df[end_col] = pd.to_datetime(event_df[end_col])
    
    total_simulated_time_steps = 0
    
    for _, row in event_df.iterrows():
        est = row[start_col]
        if pd.isna(est):
            continue
            
        # Clip start time to simulation start if event starts earlier
        if est < start_time:
            est = start_time
        
        eed = row[end_col]
        if pd.isna(eed):
            continue
            
        # Clip end time to simulation end if event ends later
        if eed > end_time:
            eed = end_time
        
        # Only count if there's an overlap with simulation period
        if est < end_time and eed > start_time:
            duration_hours = (eed - est).total_seconds() / 3600
            total_simulated_time_steps += duration_hours
    
    return min(total_simulated_time_steps, total_hours)


def _get_pod_mdl_configs_multiple(technologies, mdl_define, consider_wind, wind_speed):
    """
    Get POD (Probability of Detection) and MDL (Minimum Detection Limit) configurations for multiple technologies.
    
    Args:
        technologies: List of measurement technology names
        mdl_define: User-defined MDL value (if any technology is 'define_technology')
        consider_wind: Whether to consider wind conditions
        wind_speed: Wind speed value (required when consider_wind=True)
    
    Returns:
        Tuple of (PODs_list, MDLs_list) where:
        - PODs_list: List of POD values (functions or constants), one per technology
        - MDLs_list: List of MDL values (functions or constants), one per technology
    """
    PODs_list = []
    MDLs_list = []
    
    for technology in technologies:
        POD, MDL = _get_pod_mdl_config(technology, mdl_define, consider_wind, wind_speed)
        PODs_list.append(POD)
        MDLs_list.append(MDL)
    
    return PODs_list, MDLs_list


def _validate_and_prepare_events(events):
    """
    Validate events DataFrame and ensure required columns exist.
    
    Args:
        events: DataFrame with emission events
    
    Returns:
        Prepared events DataFrame with 'source' and 'quantity' columns
    """
    events = events.copy()
    
    # Ensure 'source' column exists
    if 'source' not in events.columns:
        if 'sourceLocation' in events.columns:
            events['source'] = events['sourceLocation']
        else:
            raise ValueError("Events DataFrame must have 'source' or 'sourceLocation' column")
    
    # Ensure 'quantity' column exists
    if 'quantity' not in events.columns:
        if 'rate' in events.columns and 'duration' in events.columns:
            events['quantity'] = events['rate'] * events['duration']
        else:
            raise ValueError("Events DataFrame must have 'quantity' column or both 'rate' and 'duration' columns")
    
    return events


def _calculate_measured_emissions(source_events, start_time, end_time):
    """
    Calculate measured emissions for a source within the simulation time range.
    
    Args:
        source_events: DataFrame with events for a single source
        start_time: Start datetime for simulation
        end_time: End datetime for simulation
    
    Returns:
        Tuple of (measured_emissions, measured_emissions_lower, measured_emissions_upper)
    """
    # Filter events that overlap with the simulation time range
    start_times = pd.to_datetime(source_events['start_time'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    end_times = pd.to_datetime(source_events['end_time'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    
    # Filter events that overlap with simulation period
    overlapping_mask = (end_times >= start_time) & (start_times <= end_time)
    overlapping_events = source_events[overlapping_mask]
    
    # Calculate total measured emissions for this source
    measured_emissions = overlapping_events['quantity'].sum() if len(overlapping_events) > 0 else 0
    
    # Calculate uncertainty for measured emissions (±20% default)
    # TODO This could be enhanced to use actual uncertainty data if available
    measured_uncertainty_pct = 0.20  # 20% uncertainty
    measured_emissions_lower = measured_emissions * (1 - measured_uncertainty_pct)
    measured_emissions_upper = measured_emissions * (1 + measured_uncertainty_pct)
    
    return measured_emissions, measured_emissions_lower, measured_emissions_upper


def _build_events_times(source_events, start_time):
    """
    Build Events_Times set and sorted array from source events.
    
    Args:
        source_events: DataFrame with events for a single source
        start_time: Start datetime for simulation
    
    Returns:
        Tuple of (Events_Times_set, Events_Times_sorted)
    """
    # Pre-parse datetime strings once (much faster than parsing in loops)
    start_times_parsed = pd.to_datetime(source_events['start_time'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    end_times_parsed = pd.to_datetime(source_events['end_time'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    
    # Build Events_Times set using pandas date_range (much faster than hour-by-hour loop)
    Events_Times_set = set()
    for st, et in zip(start_times_parsed, end_times_parsed):
        if pd.isna(st) or pd.isna(et):
            continue
        # Calculate hours since start_time for each event period
        hours_start = int((st - start_time).total_seconds() / 3600)
        hours_end = int((et - start_time).total_seconds() / 3600)
        # Add all hours in range to set
        Events_Times_set.update(range(hours_start, hours_end + 1))
    
    # Convert to sorted numpy array
    Events_Times_sorted = np.array(sorted(Events_Times_set)) if Events_Times_set else np.array([])
    
    return Events_Times_set, Events_Times_sorted


def _run_monte_carlo_simulation(
    total_hours, Events_Times_set, Events_Times_sorted, durations,
    PODs_list, wind_speed, mc_iterations, source_events=None, start_time=None, end_time=None,
    technologies=None, mdl_define=None, consider_wind=False
):
    """
    Run Monte Carlo simulation for unmeasured emissions below MDL.
    
    Args:
        total_hours: Total simulation hours
        Events_Times_set: Set of hours with measured events
        Events_Times_sorted: Sorted array of hours with measured events
        durations: Array of duration values for sampling
        PODs_list: List of Probability of Detection values (functions or constants), one per technology
        wind_speed: Wind speed value
        mc_iterations: Number of Monte Carlo iterations
        source_events: Optional DataFrame with events for calculating total simulation time steps
        start_time: Optional start datetime for calculating total simulation time steps
        end_time: Optional end datetime for calculating total simulation time steps
        technologies: List of technology names (needed for pickling POD functions)
        mdl_define: User-defined MDL value (needed for pickling POD functions)
        consider_wind: Whether wind is considered (needed for pickling POD functions)
    
    Returns:
        List of unmeasured emission values from each iteration
    """
    PARALLEL_THRESHOLD = 20
    use_parallel = mc_iterations >= PARALLEL_THRESHOLD
    
    # Convert POD functions to serializable configuration for multiprocessing
    if use_parallel and technologies is not None:
        # Create technology configuration list (picklable)
        technologies_config = []
        for tech in technologies:
            tech_config = {
                'technology': tech if tech != 'define_technology' else 'User Defined',
                'mdl_define': mdl_define if tech == 'define_technology' else None,
                'consider_wind': consider_wind
            }
            technologies_config.append(tech_config)
    else:
        # For sequential processing, use PODs_list directly
        technologies_config = None
    
    if use_parallel:
        # Prepare arguments for parallel processing
        seeds = np.random.randint(0, 2**31, size=mc_iterations)
        # Calculate total simulation time steps if event data is provided, otherwise use total_hours
        if source_events is not None and start_time is not None and end_time is not None:
            total_simulated_time_steps = calculate_total_simulation_time_steps(source_events, start_time, end_time)
        else:
            total_simulated_time_steps = total_hours
        args_list = [
            (total_simulated_time_steps, durations,
             _leaks_dist, _num_comps, technologies_config, wind_speed)
            for seed in seeds
        ]
        
        # Use multiprocessing Pool
        num_workers = min(cpu_count(), mc_iterations)
        with Pool(processes=num_workers) as pool:
            unmeasured_emissions = list(pool.map(_simulate_below_mdl_single_iteration, args_list))
    else:
        # Sequential processing for small iterations
        # Use the same helper function with sequential calls
        # Calculate total simulation time steps if event data is provided, otherwise use total_hours
        if source_events is not None and start_time is not None and end_time is not None:
            total_simulated_time_steps = calculate_total_simulation_time_steps(source_events, start_time, end_time)
        else:
            total_simulated_time_steps = total_hours
        seeds = np.random.randint(0, 2**31, size=mc_iterations)
        unmeasured_emissions = []
        for seed in seeds:
            # For sequential, pass PODs_list directly (no pickling needed)
            args = (total_simulated_time_steps, durations,
                   _leaks_dist, _num_comps, PODs_list, wind_speed)
            unmeasured_emissions.append(_simulate_below_mdl_single_iteration(args))
    
    return unmeasured_emissions


def _process_single_source(
    source_events, start_time, end_time, total_hours,
    durations, PODs_list, wind_speed, mc_iterations,
    technologies=None, mdl_define=None, consider_wind=False
):
    """
    Process a single source: calculate measured and unmeasured emissions.
    
    Args:
        source_events: DataFrame with events for a single source
        start_time: Start datetime for simulation
        end_time: End datetime for simulation
        total_hours: Total simulation hours
        durations: Array of duration values for sampling
        PODs_list: List of Probability of Detection values (functions or constants), one per technology
        wind_speed: Wind speed value
        mc_iterations: Number of Monte Carlo iterations
        technologies: List of technology names (needed for parallel processing)
        mdl_define: User-defined MDL value (needed for parallel processing)
        consider_wind: Whether wind is considered (needed for parallel processing)
    
    Returns:
        Tuple of (total_emissions, total_emissions_lower, total_emissions_upper)
    """
    # Calculate measured emissions
    measured_emissions, measured_emissions_lower, measured_emissions_upper = \
        _calculate_measured_emissions(source_events, start_time, end_time)
    
    # Build Events_Times data structures
    Events_Times_set, Events_Times_sorted = _build_events_times(source_events, start_time)
    
    # Run Monte Carlo simulation
    unmeasured_emissions = _run_monte_carlo_simulation(
        total_hours, Events_Times_set, Events_Times_sorted, durations,
        PODs_list, wind_speed, mc_iterations,
        source_events=source_events, start_time=start_time, end_time=end_time,
        technologies=technologies, mdl_define=mdl_define, consider_wind=consider_wind
    )
    
    # Calculate statistics from simulation results
    unmeasured_emissions_array = np.array(unmeasured_emissions)
    unmeasured_median = np.median(unmeasured_emissions_array)
    unmeasured_lower = np.percentile(unmeasured_emissions_array, q=2.5)
    unmeasured_upper = np.percentile(unmeasured_emissions_array, q=97.5)
    
    # Combine measured and unmeasured emissions
    total_emissions = measured_emissions + unmeasured_median
    total_emissions_lower = measured_emissions_lower + unmeasured_lower
    total_emissions_upper = measured_emissions_upper + unmeasured_upper
    
    return (total_emissions, total_emissions_lower, total_emissions_upper,
            measured_emissions, measured_emissions_lower, measured_emissions_upper,
            unmeasured_median, unmeasured_lower, unmeasured_upper)


def simulate_below_mdl(
    events,
    start_time,
    end_time,
    mc_iterations=1,
    technologies=None,
    technology=None,
    mdl_define=None,
    consider_wind=False,
    wind_speed=None,
    leak_data=None,
):
    """
    Simulate emissions below the minimum detection limit (MDL) and combine with measured emissions.
    
    For each site/source, calculates:
    1. Total measured emissions from all events within the simulation time range
    2. Simulated unmeasured emissions below detection limit
    3. Combined total emissions (measured + unmeasured) with uncertainty bounds
    
    Supports multiple technologies: an emission is detected if ANY technology detects it.
    
    Args:
        events: DataFrame with emission events (must have 'quantity', 'source'/'sourceLocation', 
                'start_time', 'end_time' columns)
        start_time: Start datetime for simulation
        end_time: End datetime for simulation
        mc_iterations: Number of Monte Carlo iterations
        technologies: List of measurement technology names (preferred). If None, uses 'technology' parameter.
        technology: Single measurement technology name (for backward compatibility).
                   Ignored if 'technologies' is provided.
        mdl_define: User-defined MDL value (if any technology is 'define_technology')
        consider_wind: Whether to consider wind conditions
        wind_speed: Wind speed value (required when consider_wind=True)
        leak_data: Optional list of leak rate values (in kg/hr). If None, loads from default file.
    
    Returns:
        Tuple of (total_emissions, lower_bound, upper_bound) where:
        - total_emissions: Sum across all sites of (measured + unmeasured) emissions
        - lower_bound: Lower 95% confidence bound for total emissions
        - upper_bound: Upper 95% confidence bound for total emissions
    """
    # Load leak data if not already loaded, or use provided leak data
    _load_leak_data(leak_data=leak_data)
    
    # Handle technology/technologies parameter (support both single and multiple)
    if technologies is None:
        if technology is None:
            raise ValueError("Either 'technologies' or 'technology' parameter must be provided")
        technologies = [technology]
    elif not isinstance(technologies, list):
        technologies = [technologies]
    
    # Get POD and MDL configurations for all technologies
    PODs_list, MDLs_list = _get_pod_mdl_configs_multiple(technologies, mdl_define, consider_wind, wind_speed)
    
    # Validate and prepare events DataFrame
    events = _validate_and_prepare_events(events)
    
    # Convert durations to numpy array for faster random choice
    durations = events.duration.values
    
    # Pre-calculate total simulation hours
    total_hours = int((end_time - start_time).total_seconds() / 3600)
    
    # Initialize accumulators
    final_total_emissions = 0
    final_total_emissions_lower = 0
    final_total_emissions_upper = 0
    final_measured_emissions = 0
    final_measured_emissions_lower = 0
    final_measured_emissions_upper = 0
    final_unmeasured_emissions = 0
    final_unmeasured_emissions_lower = 0
    final_unmeasured_emissions_upper = 0
    
    # Process each source
    for source in events['source'].unique():
        source_events = events[events['source'] == source]
        
        (total_emissions, total_emissions_lower, total_emissions_upper,
         measured_emissions, measured_emissions_lower, measured_emissions_upper,
         unmeasured_median, unmeasured_lower, unmeasured_upper) = \
            _process_single_source(
                source_events, start_time, end_time, total_hours,
                durations, PODs_list, wind_speed, mc_iterations,
                technologies=technologies, mdl_define=mdl_define, consider_wind=consider_wind
            )
        
        # Accumulate across all sources
        final_total_emissions += total_emissions
        final_total_emissions_lower += total_emissions_lower
        final_total_emissions_upper += total_emissions_upper
        final_measured_emissions += measured_emissions
        final_measured_emissions_lower += measured_emissions_lower
        final_measured_emissions_upper += measured_emissions_upper
        final_unmeasured_emissions += unmeasured_median
        final_unmeasured_emissions_lower += unmeasured_lower
        final_unmeasured_emissions_upper += unmeasured_upper

    return (final_total_emissions, final_total_emissions_lower, final_total_emissions_upper,
            final_measured_emissions, final_measured_emissions_lower, final_measured_emissions_upper,
            final_unmeasured_emissions, final_unmeasured_emissions_lower, final_unmeasured_emissions_upper)


def simulate_duration_uncertainty(leak_production_rate, events, MC_iterations=10):
    """
    Simulate duration uncertainty for emission events.
    
    Args:
        leak_production_rate: Leak production rate (probability)
        events: DataFrame with emission events (must have columns: event_type, start_time, 
                end_time, rate, duration)
        MC_iterations: Number of Monte Carlo iterations
    
    Returns:
        DataFrame with added columns: simulated_duration, simulated_duration_lower, 
        simulated_duration_upper
    """
    Q_max = events.rate.max()
    simulated_durations = []
    simulated_duration_lowers = [] 
    simulated_duration_uppers = []
    
    # Filter PRE events and pre-parse datetimes (much faster than parsing in loop)
    pre_events = events[events.event_type == "PRE"].copy()
    
    if len(pre_events) == 0:
        # No PRE events, return events with empty arrays
        events["simulated_duration"] = []
        events["simulated_duration_lower"] = []
        events["simulated_duration_upper"] = []
        return events
    
    # Pre-parse all datetime strings at once
    start_times = pd.to_datetime(pre_events['start_time'], format='%Y-%m-%d %H:%M:%S')
    end_times = pd.to_datetime(pre_events['end_time'], format='%Y-%m-%d %H:%M:%S')
    rates = pre_events['rate'].values
    durations = pre_events['duration'].values
    
    # Use parallel processing for high MC iterations (threshold: 20)
    PARALLEL_THRESHOLD = 20
    use_parallel = MC_iterations >= PARALLEL_THRESHOLD
    
    for idx in range(len(pre_events)):
        start_time = start_times.iloc[idx]
        end_time = end_times.iloc[idx]
        rate = rates[idx]
        duration = durations[idx]
        
        # Pre-calculate total hours for this event
        total_hours = int((end_time - start_time).total_seconds() / 3600)
        
        # Pre-calculate NRR (constant for this event)
        NRR = ((leak_production_rate) * 7 / 1) * (1 / 10) + (0.5 * rate) / Q_max
        
        if use_parallel:
            # Prepare arguments for parallel processing
            seeds = np.random.randint(0, 2**31, size=MC_iterations)
            args_list = [
                (total_hours, leak_production_rate, NRR, duration, int(seed))
                for seed in seeds
            ]
            
            # Use multiprocessing Pool
            num_workers = min(cpu_count(), MC_iterations)
            with Pool(processes=num_workers) as pool:
                simulated_duration_dist = pool.map(_simulate_duration_uncertainty_single_iteration, args_list)
        else:
            # Sequential processing for small iterations
            simulated_duration_dist = []
            for mc in range(MC_iterations):
                # When to start the simulation 
                sim_hour = 0
                simulated_start_hour = None 
                simulated_end_hour = None 
                
                while sim_hour < total_hours: 
                    if simulated_start_hour is None:
                        # Check for leak generation
                        sample_leak = np.random.binomial(1, leak_production_rate)
                        if sample_leak == 1: 
                            simulated_start_hour = sim_hour
                        sim_hour += 1
                    else:
                        # Check for repair
                        sample_repair = np.random.binomial(1, NRR)
                        if sample_repair == 1:
                            simulated_end_hour = sim_hour
                            break 
                        sim_hour += 1

                if simulated_start_hour is None and simulated_end_hour is None:
                    sim_duration = duration
                elif simulated_start_hour is not None and simulated_end_hour is None:
                    sim_duration = total_hours - simulated_start_hour
                else:
                    sim_duration = simulated_end_hour - simulated_start_hour
                        
                simulated_duration_dist.append(sim_duration)

        simulated_duration_dist_array = np.array(simulated_duration_dist)
        simulated_durations.append(np.mean(simulated_duration_dist_array))
        simulated_duration_lowers.append(np.percentile(simulated_duration_dist_array, 2.5))
        simulated_duration_uppers.append(np.percentile(simulated_duration_dist_array, 97.5))

    events["simulated_duration"] = simulated_durations
    events["simulated_duration_lower"] = simulated_duration_lowers
    events["simulated_duration_upper"] = simulated_duration_uppers

    return events

