"""
Simulation functions for emission estimation.

This module contains all simulation-related functions:
- extrapolation: Bootstrap simulation for unmeasured emissions
- simulate_below_mdl: Simulation for emissions below detection limit
- simulate_duration_uncertainty: Duration uncertainty simulation
"""

import numpy as np
import pandas as pd
import bisect
import os
from multiprocessing import Pool, cpu_count
from utils import probability_of_detection

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


def extrapolation(processing_resolution, prob_dist, rate_dist, duration_dist, start_time, end_time, MC):
    """
    Bootstrap simulation for unmeasured emissions (extrapolation).
    
    Args:
        processing_resolution: Processing resolution ('by_site' or other)
        prob_dist: Probability distribution dictionary
        rate_dist: Rate distribution dictionary
        duration_dist: Duration distribution dictionary
        start_time: Start datetime for simulation
        end_time: End datetime for simulation
        MC: Number of Monte Carlo iterations
    
    Returns:
        Dictionary with extrapolated emissions by source category
    """
    if processing_resolution == 'by_site':
        # only 1 source category
        final_emissions = {"UNKNOWN": []}
        poe = prob_dist.get("UNKNOWN")
        
        # Convert distributions to numpy arrays for faster access
        rate_array = np.array(rate_dist["UNKNOWN"])
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
    else: 
        return None


def hours_since_datetime(current_datetime, target_datetime):
    """Calculate hours difference between two datetimes"""
    time_difference = current_datetime - target_datetime
    hours_difference = time_difference.total_seconds() / 3600
    return hours_difference


def find_closest_after(sorted_numbers, target):
    """
    Find the closest number in a sorted list that is greater than the target.
    
    Args:
        sorted_numbers: Pre-sorted list/array of numbers (must be sorted!)
        target: Target number
    
    Returns:
        Closest number greater than target, or None if no such number exists
    """
    # Use bisect to find the insertion point for the target
    index = bisect.bisect_right(sorted_numbers, target)

    # Check if there is a number greater than the target
    if index < len(sorted_numbers):
        return sorted_numbers[index]  # Return the closest number greater than the target
    else:
        return None


def _simulate_below_mdl_single_iteration(args):
    """
    Helper function for parallel processing - simulates a single Monte Carlo iteration.
    This function must be at module level for pickling in multiprocessing.
    """
    (total_hours, Events_Times_set, Events_Times_sorted, durations, 
     leaks_dist, num_comps, POD_func_or_const, wind_speed, seed) = args
    
    # Set random seed for reproducibility in parallel execution
    np.random.seed(seed)
    
    # Check if POD is a function or constant
    is_pod_function = callable(POD_func_or_const)
    
    E_miss = 0 
    current_hour = 0
    
    while current_hour < total_hours:
        detection_label = False
        
        # Check if current hour is in Events_Times (O(1) lookup with set)
        if current_hour not in Events_Times_set:
            Q_sample = np.random.choice(leaks_dist) * np.random.choice(num_comps)
            
            # Calculate POD based on whether it's a function or constant
            if is_pod_function:
                # POD is a function of Q_sample (and possibly wind_speed)
                POD = POD_func_or_const(Q_sample)
            else:
                # POD is a constant
                POD = POD_func_or_const
            
            # Vectorize detection probability check (3 attempts)
            detection_probs = np.random.random(3)
            if np.any(POD > detection_probs):
                detection_label = True
        
        if not detection_label:
            sampled_duration = np.random.choice(durations)
            closest_number = find_closest_after(Events_Times_sorted, current_hour)
            if closest_number:
                max_time_cap = closest_number - current_hour
                sampled_duration = min(sampled_duration, max_time_cap)
                E_miss += Q_sample * sampled_duration
                # update time with sampled duration 
                current_hour += int(sampled_duration)
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


def simulate_below_mdl(
    events,
    start_time,
    end_time,
    processing_resolution,
    mc_iterations=1,
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
    
    Args:
        events: DataFrame with emission events (must have 'quantity', 'source'/'sourceLocation', 
                'start_time', 'end_time' columns)
        start_time: Start datetime for simulation
        end_time: End datetime for simulation
        processing_resolution: Processing resolution
        mc_iterations: Number of Monte Carlo iterations
        technology: Measurement technology name
        mdl_define: User-defined MDL value (if technology is 'define_technology')
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
    
    # Get POD and MDL using probability_of_detection function
    # Handle technology name mapping
    tech_name = technology
    if technology == "define_technology":
        tech_name = "User Defined"
    
    try:
        POD, MDL = probability_of_detection(
            technology=tech_name,
            wind_speed=wind_speed,
            wind_consider=consider_wind,
            standard=True,
            mdl_define=mdl_define
        )
    except ValueError as e:
        raise ValueError(f"Error getting POD/MDL for technology '{technology}': {str(e)}")
    
    # POD can be either a function (when wind_consider=True) or a constant
    # We'll pass it as-is to the helper function which will handle both cases

    # Convert durations to numpy array for faster random choice
    durations = events.duration.values
    
    final_total_emissions = 0
    final_total_emissions_lower = 0
    final_total_emissions_upper = 0
    
    # Pre-calculate total simulation hours
    total_hours = int((end_time - start_time).total_seconds() / 3600)
    
    # Ensure events DataFrame has required columns
    if 'source' not in events.columns:
        # Try alternative column names
        if 'sourceLocation' in events.columns:
            events['source'] = events['sourceLocation']
        else:
            raise ValueError("Events DataFrame must have 'source' or 'sourceLocation' column")
    
    if 'quantity' not in events.columns:
        # Calculate quantity from rate * duration if available
        if 'rate' in events.columns and 'duration' in events.columns:
            events['quantity'] = events['rate'] * events['duration']
        else:
            raise ValueError("Events DataFrame must have 'quantity' column or both 'rate' and 'duration' columns")
    
    for source in events['source'].unique():
        # For each site/source
        source_events = events[events['source'] == source]
        
        # Calculate measured emissions from all events for this source within the time range
        # Filter events that overlap with the simulation time range
        start_times = pd.to_datetime(source_events['start_time'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
        end_times = pd.to_datetime(source_events['end_time'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
        
        # Filter events that overlap with simulation period
        overlapping_mask = (end_times >= start_time) & (start_times <= end_time)
        overlapping_events = source_events[overlapping_mask]
        
        # Calculate total measured emissions for this source
        # Sum of quantity for all overlapping events
        measured_emissions = overlapping_events['quantity'].sum() if len(overlapping_events) > 0 else 0
        
        # Calculate uncertainty for measured emissions (±20% default)
        # TODO This could be enhanced to use actual uncertainty data if available
        measured_uncertainty_pct = 0.20  # 20% uncertainty
        measured_emissions_lower = measured_emissions * (1 - measured_uncertainty_pct)
        measured_emissions_upper = measured_emissions * (1 + measured_uncertainty_pct)
        
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
        
        # Convert to sorted numpy array for find_closest_after
        Events_Times_sorted = np.array(sorted(Events_Times_set)) if Events_Times_set else np.array([])
        
        # Use parallel processing for high MC iterations (threshold: 20)
        PARALLEL_THRESHOLD = 20
        use_parallel = mc_iterations >= PARALLEL_THRESHOLD
        
        if use_parallel:
            # Prepare arguments for parallel processing
            # Use different seeds for each iteration to ensure randomness
            seeds = np.random.randint(0, 2**31, size=mc_iterations)
            args_list = [
                (total_hours, Events_Times_set, Events_Times_sorted, durations,
                 _leaks_dist, _num_comps, POD, wind_speed, int(seed))
                for seed in seeds
            ]
            
            # Use multiprocessing Pool
            num_workers = min(cpu_count(), mc_iterations)  # Don't use more workers than iterations
            with Pool(processes=num_workers) as pool:
                Unmeasured_emissions = pool.map(_simulate_below_mdl_single_iteration, args_list)
        else:
            # Sequential processing for small iterations
            # Check if POD is a function or constant
            is_pod_function = callable(POD)
            
            Unmeasured_emissions = []
            for mc in range(mc_iterations):
                E_miss = 0 
                current_hour = 0
                
                while current_hour < total_hours:
                    detection_label = False
                    
                    # Check if current hour is in Events_Times (O(1) lookup with set)
                    if current_hour not in Events_Times_set:
                        Q_sample = np.random.choice(_leaks_dist) * np.random.choice(_num_comps)
                        
                        # Calculate POD based on whether it's a function or constant
                        if is_pod_function:
                            # POD is a function of Q_sample (and possibly wind_speed)
                            pod_value = POD(Q_sample)
                        else:
                            # POD is a constant
                            pod_value = POD
                        
                        # Vectorize detection probability check (3 attempts)
                        detection_probs = np.random.random(3)
                        if np.any(pod_value > detection_probs):
                            detection_label = True
                    
                    if not detection_label:
                        sampled_duration = np.random.choice(durations)
                        if len(Events_Times_sorted) > 0:
                            closest_number = find_closest_after(Events_Times_sorted, current_hour)
                            if closest_number:
                                max_time_cap = closest_number - current_hour
                                sampled_duration = min(sampled_duration, max_time_cap)
                                E_miss += Q_sample * sampled_duration
                                # update time with sampled duration 
                                current_hour += int(sampled_duration)
                            else: 
                                # update time by adding 1 hour 
                                current_hour += 1
                        else:
                            E_miss += Q_sample * sampled_duration
                            current_hour += int(sampled_duration)
                            
                Unmeasured_emissions.append(E_miss)
            
        Unmeasured_emissions_array = np.array(Unmeasured_emissions)
        unmeasured_median = np.median(Unmeasured_emissions_array)
        unmeasured_lower = np.percentile(Unmeasured_emissions_array, q=2.5)
        unmeasured_upper = np.percentile(Unmeasured_emissions_array, q=97.5)
        
        # Combine measured and unmeasured emissions
        # Total emissions = measured + unmeasured
        total_emissions = measured_emissions + unmeasured_median
        
        # For uncertainty bounds, we add the uncertainties (conservative approach)
        # Lower bound: measured_lower + unmeasured_lower
        # Upper bound: measured_upper + unmeasured_upper
        total_emissions_lower = measured_emissions_lower + unmeasured_lower
        total_emissions_upper = measured_emissions_upper + unmeasured_upper
        
        # Accumulate across all sources
        final_total_emissions += total_emissions
        final_total_emissions_lower += total_emissions_lower
        final_total_emissions_upper += total_emissions_upper

    return final_total_emissions, final_total_emissions_lower, final_total_emissions_upper


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

