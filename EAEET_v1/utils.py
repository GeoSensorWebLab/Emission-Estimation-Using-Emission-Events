"""
Utility functions for emission estimation toolkit.

This module contains utility functions for statistical analysis and data correction:
- fitting_distribution: Fit statistical distributions to data
- quantification_correction: Apply uncertainty bounds to rate measurements
- duration_correction: Apply uncertainty bounds to duration measurements
"""

import numpy as np
from scipy.stats import lognorm, norm, uniform, expon, weibull_min, gamma


def quantification_correction(
    rates, lower_uncertainty_bound, upper_uncertainty_bound, iterations=1000
):
    """
    Apply quantification correction with uncertainty bounds to emission rates.
    
    Args:
        rates: Array of emission rates
        lower_uncertainty_bound: Lower bound for uncertainty multiplier
        upper_uncertainty_bound: Upper bound for uncertainty multiplier
        iterations: Number of Monte Carlo iterations
    
    Returns:
        List of sampled rates with applied uncertainty
    """
    sampled_rates = []
    for mc in range(iterations):
        for rate in rates:
            rate_sample = np.random.choice(rates, size=1, replace=True)
            rate_sample = (
                rate_sample
                * np.random.uniform(
                    lower_uncertainty_bound, upper_uncertainty_bound, size=1
                )[0]
            )
            sampled_rates.append(rate_sample)

    return sampled_rates


def duration_correction(durations, lower_uncertainty_bound, upper_uncertainty_bound, iterations=1000):
    """
    Apply duration correction with uncertainty bounds to emission durations.
    
    Args:
        durations: Array of emission durations
        lower_uncertainty_bound: Lower bound for uncertainty multiplier
        upper_uncertainty_bound: Upper bound for uncertainty multiplier
        iterations: Number of Monte Carlo iterations
    
    Returns:
        List of sampled durations with applied uncertainty
    """
    sampled_durations = []
    for mc in range(iterations):
        for duration in durations:
            duration_sample = np.random.choice(durations, size=1, replace=True)
            duration_sample = (
                duration_sample
                * np.random.uniform(lower_uncertainty_bound, upper_uncertainty_bound, size=1)[0]
            )
            sampled_durations.append(duration_sample)
    return sampled_durations


def fitting_distribution(data, distribution_type="lognormal"):
    """
    Fit a statistical distribution to data.
    
    Args:
        data: Array of data points to fit
        distribution_type: Type of distribution to fit. Options:
            - "lognormal": Log-normal distribution
            - "normal": Normal distribution
            - "uniform": Uniform distribution
            - "exponential": Exponential distribution
            - "weibull": Weibull distribution
            - "gamma": Gamma distribution
    
    Returns:
        Distribution parameters (shape, location, scale)
    """
    if distribution_type == "lognormal":
        return lognorm.fit(data, floc=0)
    elif distribution_type == "normal":
        return norm.fit(data, floc=0)
    elif distribution_type == "uniform":
        return uniform.fit(data, floc=0)
    elif distribution_type == "exponential":
        return expon.fit(data, floc=0)
    elif distribution_type == "weibull":
        return weibull_min.fit(data, floc=0)
    elif distribution_type == "gamma":
        return gamma.fit(data, floc=0)

def probability_of_detection(technology, wind_speed=None, wind_consider=False, mdl_define=None):
    """
    Get Probability of Detection (POD) and Minimum Detection Limit (MDL) for a given technology.
    
    Args:
        technology: Technology name (e.g., "InsightM", "Qube", "SeekOps", etc.)
        wind_speed: Wind speed value (required when wind_consider=True)
        wind_consider: Whether to consider wind effects (default: False)
        mdl_define: User-defined MDL value for "User Defined" technology
    
    Returns:
        tuple: (POD, MDL) where:
            - POD: Either a constant (float) or a function that takes Q_sample and returns POD
            - MDL: Either a constant (float) or a function that takes Q_sample and returns MDL
    
    Note:
        When wind_consider=True, POD and MDL are returned as functions that take Q_sample as input.
        When wind_consider=False, POD and MDL are returned as constants.
    """
    # Helper function to create POD function with wind consideration
    def _create_pod_function_with_wind(coeff_a, coeff_b, ws, formula_type='logistic'):
        """Create POD function based on formula type"""
        if formula_type == 'insightm':
            def pod_func(Q_sample):
                return 1 - (1 + (((coeff_a / ws**coeff_b) * Q_sample**1.87)**2))**-1.5
            return pod_func
        else:  # logistic
            def pod_func(Q_sample):
                return 1 / (1 + np.exp(coeff_a - coeff_b * (Q_sample / ws)))
            return pod_func
    
    # Helper function for MDL when wind is considered (MDL = Q_sample)
    def _mdl_with_wind(Q_sample):
        return Q_sample
    
    if technology == "InsightM":
        if wind_consider:
            if wind_speed is None:
                raise ValueError("wind_speed is required when wind_consider=True")
            POD = _create_pod_function_with_wind(0.00771, 1.41, wind_speed, formula_type='insightm')
            MDL = _mdl_with_wind
        else:
            POD = 0.9
            MDL = 10
                
    elif technology == "Qube":
        if wind_consider:
            if wind_speed is None:
                raise ValueError("wind_speed is required when wind_consider=True")
            POD = _create_pod_function_with_wind(-0.309, 1.047, wind_speed)
            MDL = _mdl_with_wind
        else:
            POD = 0.9
            MDL = 2
            
    elif technology == "SeekOps":
        POD = 0.9
        MDL = 0.02
        
    elif technology == "Bridger Photonic":
        if wind_consider:
            if wind_speed is None:
                raise ValueError("wind_speed is required when wind_consider=True")
            POD = _create_pod_function_with_wind(5.222, 30.286, wind_speed)
            MDL = _mdl_with_wind
        else:
            POD = 0.9
            MDL = 0.5
        
    elif technology == "GHGSat-Air":
        POD = 0.9
        MDL = 13.6
        
    elif technology == "Kuva Systems":
        if wind_consider:
            if wind_speed is None:
                raise ValueError("wind_speed is required when wind_consider=True")
            POD = _create_pod_function_with_wind(6.01, 0.13, wind_speed)
            MDL = _mdl_with_wind
        else:
            POD = 0.9
            MDL = 3.5
            
    elif technology == "Sensirion":
        if wind_consider:
            if wind_speed is None:
                raise ValueError("wind_speed is required when wind_consider=True")
            POD = _create_pod_function_with_wind(-6.41, 0.505, wind_speed)
            MDL = _mdl_with_wind
        else:
            POD = 0.9
            MDL = 3.6
            
    elif technology == "Aeromon":
        POD = 0.9
        MDL = 0.1
        
    elif technology == "Project Canary":
        if wind_consider:
            if wind_speed is None:
                raise ValueError("wind_speed is required when wind_consider=True")
            POD = _create_pod_function_with_wind(-1.661, 2.724, wind_speed)
            MDL = _mdl_with_wind
        else:
            POD = 0.9
            MDL = 0.2
            
    elif technology == "Long Path":
        POD = 0.9
        MDL = 0.06
        
    elif technology == "User Defined" or technology == "define_technology":
        if mdl_define is None:
            raise ValueError("mdl_define is required for User Defined technology")
        POD = mdl_define
        MDL = mdl_define
        
    else:
        raise ValueError(f"Unknown technology: {technology}")
    
    return POD, MDL