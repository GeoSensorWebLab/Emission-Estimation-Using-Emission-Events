"""
Emission Event Converter Module
This module handles conversion of site-level measurement data to Emission Event UML model structure.
Implements Allen's Interval Algebra for temporal event merging.
Reference: https://en.wikipedia.org/wiki/Allen%27s_interval_algebra
"""
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid


def convert_to_emission_event_model(data: pd.DataFrame, column_mapping: Optional[Dict[str, str]] = None, 
                                    time_column: Optional[str] = None,
                                    emission_characteristics: str = 'intermittent') -> pd.DataFrame:
    """
    Convert site-level measurement data to Emission Event data model.
    Based on UML: Emission Event has eventType, and relationships to:
    - Quantity (calculated from rate * duration)
    - Observation (quantity/rate, duration)
    - Duration (duration, durationEstimationType)
    - Cause (root cause analysis)
    - Source (sourceLocation, sourceCategory, physicalSource)
    
    Implements temporal event creation and merging using Allen's Interval Algebra:
    1. Creates initial events from detections (rate > 0)
    2. Determines start/end times based on non-detects (rate = 0)
    3. Merges events using Allen's temporal relations
    
    Args:
        data: DataFrame with uploaded data
        column_mapping: Dictionary mapping required fields to actual column names.
                       Required keys: 'rate', 'id', 'source'
                       Optional keys: 'cause', 'duration', 'time', 'emission_characteristics', 'uncertainties', 'source_scale'
                       Note: 'source_scale' defaults to 'site' if not provided
        time_column: Name of time/timestamp column (optional, will try to auto-detect)
        emission_characteristics: 'continuous' or 'intermittent'. If 'continuous', each row is an independent event.
                                 If 'intermittent', events are merged using Allen's interval algebra.
    
    Returns:
        DataFrame with converted emission events (flattened structure)
    
    Raises:
        ValueError: If required columns are missing or not mapped
    """
    # Use column mapping if provided, otherwise try to auto-detect
    if column_mapping:
        rate_col = column_mapping.get('rate')
        uncertainties_col = column_mapping.get('uncertainties')
        id_col = column_mapping.get('id')
        # source_scale removed from mapping - defaults to 'site'
        source_scale_value = column_mapping.get('source_scale', 'site')  # Default to 'site' if not provided
        source_col = column_mapping.get('source')
        cause_col = column_mapping.get('cause')
        start_time_col = column_mapping.get('start_time')
        end_time_col = column_mapping.get('end_time')
        observation_type_col = column_mapping.get('observation_type')  # Optional: column indicating observation type (used to determine operational status)
        time_col = time_column or column_mapping.get('time')
    else:
        # Auto-detect columns
        rate_col = 'rate' if 'rate' in data.columns else None
        uncertainties_col = 'uncertainties' if 'uncertainties' in data.columns else None
        id_col = 'id' if 'id' in data.columns else None
        source_scale_value = 'site'  # Default value
        source_col = 'source' if 'source' in data.columns else None
        cause_col = 'cause' if 'cause' in data.columns else None
        start_time_col = 'start_time' if 'start_time' in data.columns else ('startTime' if 'startTime' in data.columns else None)
        end_time_col = 'end_time' if 'end_time' in data.columns else ('endTime' if 'endTime' in data.columns else None)
        observation_type_col = 'observation_type' if 'observation_type' in data.columns else ('observationType' if 'observationType' in data.columns else ('Observation_Type' if 'Observation_Type' in data.columns else None))
        time_col = time_column
    
    # Auto-detect time column if not provided
    if not time_col:
        time_candidates = ['time', 'timestamp', 'datetime', 'date', 'detectionTime', 
                          'surveyTime', 'startTime', 'start_time', 'endTime', 'end_time']
        for candidate in time_candidates:
            if candidate in data.columns:
                time_col = candidate
                break
    
    # Validate mandatory fields
    if not rate_col or rate_col not in data.columns:
        raise ValueError("Rate column is required but not found or not mapped")
    if not id_col or id_col not in data.columns:
        raise ValueError("ID column is required but not found or not mapped")
    if not source_col or source_col not in data.columns:
        raise ValueError("Source column is required but not found or not mapped")
    # source_scale defaults to 'site' if not provided
    if not source_scale_value:
        source_scale_value = 'site'
    
    # Get emission characteristics from mapping or parameter
    emission_char = column_mapping.get('emission_characteristics', emission_characteristics) if column_mapping else emission_characteristics
    emission_char = emission_char.lower() if emission_char else 'intermittent'
    
    # Step 1: Create initial events from detections with temporal boundaries
    if time_col and time_col in data.columns:
            # Use temporal event creation logic
            emission_events = create_initial_events(data, {
                'rate': rate_col,
                'uncertainties': uncertainties_col,
                'id': id_col,
                'source': source_col,
                'source_scale': source_scale_value,  # This is now the enum value, not a column
                'cause': cause_col,
                'start_time': start_time_col,
                'end_time': end_time_col,
                'observation_type': observation_type_col  # Pass observation_type column mapping
            }, time_col)
            
            # Step 2: Merge events using Allen's interval algebra (only if intermittent)
            if emission_char == 'intermittent':
                emission_events = merge_events_by_allen_algebra(emission_events)
            # If continuous, skip merging - each row is an independent event
    else:
        # Fallback to original logic if no time column
        emission_events = []
        for idx, row in data.iterrows():
            # Only process detections (rate > 0)
            rate = pd.to_numeric(row.get(rate_col, 0), errors='coerce')
            if pd.isna(rate) or rate == 0:
                continue
            
            # Get uncertainties if available
            uncertainties = None
            if uncertainties_col and uncertainties_col in data.columns:
                uncertainties_val = row.get(uncertainties_col)
                if pd.notna(uncertainties_val):
                    uncertainties = pd.to_numeric(uncertainties_val, errors='coerce')
                    if pd.isna(uncertainties):
                        uncertainties = None
            
            original_data_id = str(row.get(id_col, idx))
            # Generate UUID for event ID
            event_id = str(uuid.uuid4())
            # source_scale is now a direct enum value, not from a column
            # source_scale is now a direct enum value, not from a column
            source_scale = str(source_scale_value).lower()
            source_name = str(row.get(source_col, 'Unknown'))
            
            # Start time and end time handling
            start_time = None
            end_time = None
            duration = 0
            
            # If start_time and end_time columns are provided, use them
            if start_time_col and start_time_col in data.columns and end_time_col and end_time_col in data.columns:
                start_time_val = row.get(start_time_col)
                end_time_val = row.get(end_time_col)
                if pd.notna(start_time_val) and pd.notna(end_time_val):
                    try:
                        start_time = pd.to_datetime(start_time_val)
                        end_time = pd.to_datetime(end_time_val)
                        duration = (end_time - start_time).total_seconds() / 3600
                        duration_estimation_type = 'Measured'
                    except (ValueError, TypeError):
                        duration_estimation_type = 'Estimated'
                else:
                    duration_estimation_type = 'Estimated'
            else:
                duration_estimation_type = 'Estimated'
            
            # Cause handling (optional)
            cause_value = None
            if cause_col and cause_col in data.columns:
                cause_value = str(row.get(cause_col, ''))
                if cause_value == 'nan' or cause_value == '':
                    cause_value = None
            
            # Get observation_type from original data to determine operational status
            # Resolved events (RE): observation_type == "operation"
            # Partially resolved events (PRE): observation_type != "operation"
            is_operational = False  # Track if this is an operational event
            if observation_type_col and observation_type_col in data.columns:
                observation_type_value = str(row.get(observation_type_col, '')).strip().lower()
                # Check if observation_type equals "operation" (case-insensitive)
                if observation_type_value == 'operation':
                    is_operational = True
                else:
                    is_operational = False
            
            # Calculate quantity (rate * duration)
            quantity = rate * duration if duration > 0 else rate
            
            # Create emission event following UML structure
            event = {
                'id': event_id,
                'original_data_id': original_data_id,  # Store original data ID separately
                'eventType': 'Emission Event',
                'is_operational': is_operational,  # Track operational status (True if observation_type == "operation")
                'quantity': {
                    'value': quantity,
                    'unit': 'kg'
                },
                'observation': {
                    'quantity': rate,
                    'duration': duration
                },
                'duration': {
                    'duration': duration,
                    'durationEstimationType': duration_estimation_type
                },
                'cause': {
                    'rootCauseAnalysis': cause_value
                } if cause_value else None,
                'source': {
                    'sourceLocation': source_name,
                    'sourceCategory': source_scale,
                    'physicalSource': source_name
                },
                'rate': rate,
                'uncertainties': uncertainties,
                'source_scale': source_scale,
                'source_name': source_name,
                'startTime': start_time.isoformat() if start_time else None,
                'endTime': end_time.isoformat() if end_time else None
            }
            emission_events.append(event)
    
    # Convert to DataFrame for easier display (flattened structure)
    events_list = []
    for e in emission_events:
        # Format merged_from: show list of original data IDs
        merged_from_display = None
        if 'merged_from' in e and e['merged_from']:
            # merged_from is already a list of original data IDs (for merged events)
            if isinstance(e['merged_from'], list):
                merged_from_display = ', '.join(str(oid) for oid in e['merged_from'])
            else:
                merged_from_display = str(e['merged_from'])
        elif 'original_data_id' in e:
            # Single event (not merged), still show its original data ID
            merged_from_display = str(e['original_data_id'])
        
        # Format startTime and endTime to strings if they're datetime objects
        start_time = e.get('startTime')
        if start_time and not isinstance(start_time, str):
            start_time = start_time.isoformat() if hasattr(start_time, 'isoformat') else str(start_time)
        
        end_time = e.get('endTime')
        if end_time and not isinstance(end_time, str):
            end_time = end_time.isoformat() if hasattr(end_time, 'isoformat') else str(end_time)
        
        # Determine event_type: RE if operational (observation_type == "operation"), PRE if non-operational (observation_type != "operation")
        is_operational = e.get('is_operational', False)
        if is_operational:
            event_type = 'RE'  # Resolved - includes data with observation_type == "operation"
        else:
            event_type = 'PRE'  # Partially Resolved - only includes data with observation_type != "operation"
        
        event_dict = {
            'id': e['id'],
            'rate': e['rate'],
            'duration': e['duration']['duration'],
            'quantity': e['quantity']['value'],
            'sourceLocation': e['source']['sourceLocation'],
            'startTime': start_time,
            'endTime': end_time,
            'merged_from': merged_from_display,
            'event_type': event_type  # Add event_type to output
        }
        # Add uncertainties if available
        if 'uncertainties' in e and e['uncertainties'] is not None:
            event_dict['uncertainties'] = e['uncertainties']
        events_list.append(event_dict)
    
    events_df = pd.DataFrame(events_list)
    
    # Calculate statistics: resolved vs partially resolved events
    resolved_count = len(events_df[events_df['event_type'] == 'RE']) if 'event_type' in events_df.columns else 0
    partially_resolved_count = len(events_df[events_df['event_type'] == 'PRE']) if 'event_type' in events_df.columns else 0
    total_events = len(events_df)
    
    # Store statistics as attributes (can be accessed via events_df.attrs)
    events_df.attrs['resolved_count'] = resolved_count
    events_df.attrs['partially_resolved_count'] = partially_resolved_count
    events_df.attrs['total_events'] = total_events
    
    return events_df


# Allen's Interval Algebra Relations
# Based on: https://en.wikipedia.org/wiki/Allen%27s_interval_algebra

def check_allen_relation(event1_start: datetime, event1_end: datetime, 
                         event2_start: datetime, event2_end: datetime) -> List[str]:
    """
    Check which Allen's interval algebra relations hold between two events.
    
    Returns list of relations that are true:
    - 'before' (<): event1 ends before event2 starts
    - 'meets' (m): event1 ends exactly when event2 starts
    - 'overlaps' (o): event1 starts before event2, but they overlap
    - 'starts' (s): event1 starts when event2 starts, but event1 ends before event2
    - 'during' (d): event1 is completely contained within event2
    - 'finishes' (f): event1 ends when event2 ends, but event1 starts after event2
    - 'equals' (=): event1 and event2 have the same start and end times
    
    Args:
        event1_start: Start time of first event
        event1_end: End time of first event
        event2_start: Start time of second event
        event2_end: End time of second event
    
    Returns:
        List of relation strings that are true
    """
    relations = []
    
    # Ensure times are datetime objects
    if isinstance(event1_start, str):
        event1_start = pd.to_datetime(event1_start)
    if isinstance(event1_end, str):
        event1_end = pd.to_datetime(event1_end)
    if isinstance(event2_start, str):
        event2_start = pd.to_datetime(event2_start)
    if isinstance(event2_end, str):
        event2_end = pd.to_datetime(event2_end)
    
    # before (<): event1 ends before event2 starts
    if event1_end < event2_start:
        relations.append('before')
    
    # meets (m): event1 ends exactly when event2 starts
    if event1_end == event2_start:
        relations.append('meets')
    
    # overlaps (o): event1 starts before event2, overlaps, but ends before event2 ends
    if event1_start < event2_start < event1_end < event2_end:
        relations.append('overlaps')
    
    # starts (s): event1 starts when event2 starts, but event1 ends before event2
    if event1_start == event2_start and event1_end < event2_end:
        relations.append('starts')
    
    # during (d): event1 is completely contained within event2
    if event2_start < event1_start and event1_end < event2_end:
        relations.append('during')
    
    # finishes (f): event1 ends when event2 ends, but event1 starts after event2
    if event1_start > event2_start and event1_end == event2_end:
        relations.append('finishes')
    
    # equals (=): same start and end
    if event1_start == event2_start and event1_end == event2_end:
        relations.append('equals')
    
    return relations


def can_merge_events(event1: Dict, event2: Dict) -> bool:
    """
    Check if two events can be merged based on Allen's interval algebra.
    Events can be merged if they:
    1. Have the same source
    2. Overlap or are adjacent in time (not separated by a gap)
    
    Args:
        event1: First event dictionary
        event2: Second event dictionary
    
    Returns:
        True if events can be merged, False otherwise
    """
    # Check if same source
    source1 = event1.get('source', {}).get('physicalSource', '')
    source2 = event2.get('source', {}).get('physicalSource', '')
    
    # Also check sourceLocation for compatibility
    if source1 != source2:
        source_loc1 = event1.get('source', {}).get('sourceLocation', '')
        source_loc2 = event2.get('source', {}).get('sourceLocation', '')
        if source_loc1 != source_loc2:
            return False
    
    # Get time intervals
    start1 = event1.get('startTime')
    end1 = event1.get('endTime')
    start2 = event2.get('startTime')
    end2 = event2.get('endTime')
    
    if None in [start1, end1, start2, end2]:
        return False
    
    # Convert to datetime if needed
    if isinstance(start1, str):
        start1 = pd.to_datetime(start1)
    if isinstance(end1, str):
        end1 = pd.to_datetime(end1)
    if isinstance(start2, str):
        start2 = pd.to_datetime(start2)
    if isinstance(end2, str):
        end2 = pd.to_datetime(end2)
    
    # Check if events overlap or are adjacent
    # Two events overlap if: start1 < end2 AND start2 < end1
    # They are adjacent if: end1 == start2 OR end2 == start1
    # They can be merged if they overlap OR are adjacent (meets relation)
    overlap = (start1 < end2) and (start2 < end1)
    adjacent = (end1 == start2) or (end2 == start1)
    
    return overlap or adjacent


def merge_events(event1: Dict, event2: Dict) -> Dict:
    """
    Merge two events into a single event.
    - Average the rates
    - Average the uncertainties (if available)
    - Combine the time intervals (min start, max end)
    - Recalculate duration and quantity
    
    Args:
        event1: First event dictionary
        event2: Second event dictionary
    
    Returns:
        Merged event dictionary
    """
    # Get rates
    rate1 = event1.get('rate', 0)
    rate2 = event2.get('rate', 0)
    
    # Average the rates
    avg_rate = (rate1 + rate2) / 2
    
    # Get uncertainties and average if both available
    uncertainties1 = event1.get('uncertainties')
    uncertainties2 = event2.get('uncertainties')
    avg_uncertainties = None
    if uncertainties1 is not None and uncertainties2 is not None:
        avg_uncertainties = (uncertainties1 + uncertainties2) / 2
    elif uncertainties1 is not None:
        avg_uncertainties = uncertainties1
    elif uncertainties2 is not None:
        avg_uncertainties = uncertainties2
    
    # Get time intervals
    start1 = pd.to_datetime(event1.get('startTime'))
    end1 = pd.to_datetime(event1.get('endTime'))
    start2 = pd.to_datetime(event2.get('startTime'))
    end2 = pd.to_datetime(event2.get('endTime'))
    
    # Combine intervals: min start, max end
    merged_start = min(start1, start2)
    merged_end = max(end1, end2)
    
    # Calculate duration in hours
    duration = (merged_end - merged_start).total_seconds() / 3600
    
    # Recalculate quantity
    quantity = avg_rate * duration if duration > 0 else avg_rate
    
    # Merge other attributes (prefer non-None values)
    cause1 = event1.get('cause', {}).get('rootCauseAnalysis') if event1.get('cause') else None
    cause2 = event2.get('cause', {}).get('rootCauseAnalysis') if event2.get('cause') else None
    merged_cause = cause1 if cause1 else cause2
    
    # Collect original data IDs from both events
    original_ids = []
    if 'original_data_id' in event1:
        original_ids.append(event1['original_data_id'])
    elif 'merged_from' in event1:
        # If event1 was already merged, get its original IDs
        merged_from_1 = event1.get('merged_from', [])
        if isinstance(merged_from_1, list):
            original_ids.extend(merged_from_1)
        else:
            original_ids.append(str(merged_from_1))
    
    if 'original_data_id' in event2:
        original_ids.append(event2['original_data_id'])
    elif 'merged_from' in event2:
        # If event2 was already merged, get its original IDs
        merged_from_2 = event2.get('merged_from', [])
        if isinstance(merged_from_2, list):
            original_ids.extend(merged_from_2)
        else:
            original_ids.append(str(merged_from_2))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_original_ids = []
    for oid in original_ids:
        if oid not in seen:
            seen.add(oid)
            unique_original_ids.append(oid)
    
    # Determine operational status: merged event is operational if at least one event is operational
    is_operational1 = event1.get('is_operational', False)
    is_operational2 = event2.get('is_operational', False)
    merged_is_operational = is_operational1 or is_operational2
    
    # Generate UUID for merged event
    merged_event_id = str(uuid.uuid4())
    
    # Create merged event
    merged_event = {
        'id': merged_event_id,
        'eventType': event1.get('eventType', 'Emission Event'),
        'is_operational': merged_is_operational,  # True if at least one merged event has observation_type == "operation" (RE)
        'quantity': {
            'value': quantity,
            'unit': 'kg'
        },
        'observation': {
            'quantity': avg_rate,
            'duration': duration
        },
        'duration': {
            'duration': duration,
            'durationEstimationType': 'Measured'
        },
        'cause': {
            'rootCauseAnalysis': merged_cause
        } if merged_cause else None,
        'source': event1.get('source', {}),
        'rate': avg_rate,
        'uncertainties': avg_uncertainties,
        'source_scale': event1.get('source_scale', ''),
        'source_name': event1.get('source_name', ''),
        'startTime': merged_start.isoformat() if hasattr(merged_start, 'isoformat') else merged_start,
        'endTime': merged_end.isoformat() if hasattr(merged_end, 'isoformat') else merged_end,
        'merged_from': unique_original_ids  # Store list of original data IDs
    }
    
    return merged_event


def _calculate_temporal_boundaries(source_data: pd.DataFrame, detection_time: pd.Timestamp, 
                                   time_col: str, rate_col: str) -> tuple:
    """
    Calculate start and end times for an event based on non-detects.
    
    Args:
        source_data: DataFrame filtered to a single source
        detection_time: Timestamp of the detection
        time_col: Name of the time column
        rate_col: Name of the rate column
    
    Returns:
        Tuple of (start_time, end_time)
    """
    # Find start time: most recent non-detect before this detection
    non_detects_before = source_data[
        (source_data[time_col] < detection_time) & 
        (pd.to_numeric(source_data[rate_col], errors='coerce') == 0)
    ]
    
    if len(non_detects_before) > 0:
        start_time = non_detects_before[time_col].iloc[-1]
    else:
        # Default: 180 days before detection if no non-detect found
        start_time = detection_time - timedelta(days=180)
    
    # Find end time: next non-detect after this detection
    non_detects_after = source_data[
        (source_data[time_col] > detection_time) & 
        (pd.to_numeric(source_data[rate_col], errors='coerce') == 0)
    ]
    
    if len(non_detects_after) > 0:
        end_time = non_detects_after[time_col].iloc[0]
    else:
        # Default: 1 hour after detection if no non-detect found
        end_time = detection_time + timedelta(hours=1)
    
    return start_time, end_time


def create_initial_events(data: pd.DataFrame, column_mapping: Dict[str, str], 
                          time_col: str) -> List[Dict]:
    """
    Create initial events from data rows.
    For each detection (rate > 0):
    - Start time = most recent non-detect (rate=0) for same source before this detection
    - End time = next non-detect (rate=0) for same source after this detection
    
    Args:
        data: DataFrame with measurement data
        column_mapping: Column mapping dictionary
        time_col: Name of the time/timestamp column
    
    Returns:
        List of initial event dictionaries
    """
    events = []
    
    rate_col = column_mapping.get('rate')
    uncertainties_col = column_mapping.get('uncertainties')
    id_col = column_mapping.get('id')
    source_col = column_mapping.get('source')
    # source_scale is now a direct enum value ('site', 'equipment', 'component'), not a column name
    source_scale_value = column_mapping.get('source_scale')
    cause_col = column_mapping.get('cause')
    start_time_col = column_mapping.get('start_time')
    end_time_col = column_mapping.get('end_time')
    observation_type_col = column_mapping.get('observation_type')  # Optional: column indicating observation type (used to determine operational status)
    
    # Ensure time column is datetime
    if time_col not in data.columns:
        raise ValueError(f"Time column '{time_col}' not found in data")
    
    data = data.copy()
    data[time_col] = pd.to_datetime(data[time_col])
    data = data.sort_values(by=[source_col, time_col]).reset_index(drop=True)
    
    # Group by source
    for source_name, source_group in data.groupby(source_col):
        source_data = source_group.sort_values(by=time_col).reset_index(drop=True)
        
        # Find all detections (rate > 0)
        detections = source_data[source_data[rate_col] > 0].copy()
        
        for idx, row in detections.iterrows():
            detection_time = row[time_col]
            detection_rate = pd.to_numeric(row[rate_col], errors='coerce')
            if pd.isna(detection_rate):
                continue
            
            # Get uncertainties if available
            detection_uncertainties = None
            if uncertainties_col and uncertainties_col in source_data.columns:
                uncertainties_val = row.get(uncertainties_col)
                if pd.notna(uncertainties_val):
                    detection_uncertainties = pd.to_numeric(uncertainties_val, errors='coerce')
                    if pd.isna(detection_uncertainties):
                        detection_uncertainties = None
            
            # Check if start_time and end_time columns are provided
            if start_time_col and start_time_col in data.columns and end_time_col and end_time_col in data.columns:
                # Use provided start_time and end_time columns
                start_time_val = row.get(start_time_col)
                end_time_val = row.get(end_time_col)
                if pd.notna(start_time_val) and pd.notna(end_time_val):
                    try:
                        start_time = pd.to_datetime(start_time_val)
                        end_time = pd.to_datetime(end_time_val)
                    except (ValueError, TypeError):
                        # Fall back to time-based logic if parsing fails
                        start_time, end_time = _calculate_temporal_boundaries(
                            source_data, detection_time, time_col, rate_col
                        )
                else:
                    # Fall back to time-based logic if values are missing
                    start_time, end_time = _calculate_temporal_boundaries(
                        source_data, detection_time, time_col, rate_col
                    )
            else:
                # Use time-based logic: find start/end from non-detects
                start_time, end_time = _calculate_temporal_boundaries(
                    source_data, detection_time, time_col, rate_col
                )
            
            # Calculate duration
            duration = (end_time - start_time).total_seconds() / 3600
            
            # Get other attributes
            original_data_id = str(row.get(id_col, f"{source_name}_{detection_time}"))
            # Generate UUID for event ID
            event_id = str(uuid.uuid4())
            # source_scale is now a direct enum value, not from a column
            source_scale = str(source_scale_value).lower()
            
            cause_value = None
            if cause_col and cause_col in source_data.columns:
                cause_value = str(row.get(cause_col, ''))
                if cause_value == 'nan' or cause_value == '':
                    cause_value = None
            
            # Get observation_type from original data to determine operational status
            # Resolved events (RE): observation_type == "operation"
            # Partially resolved events (PRE): observation_type != "operation"
            is_operational = False  # Track if this is an operational event
            if observation_type_col and observation_type_col in source_data.columns:
                observation_type_value = str(row.get(observation_type_col, '')).strip().lower()
                # Check if observation_type equals "operation" (case-insensitive)
                if observation_type_value == 'operation':
                    is_operational = True
                else:
                    is_operational = False
            
            # Calculate quantity
            quantity = detection_rate * duration if duration > 0 else detection_rate
            
            # Create event
            event = {
                'id': event_id,
                'original_data_id': original_data_id,  # Store original data ID separately
                'eventType': 'Emission Event',
                'is_operational': is_operational,  # Track operational status (True if observation_type == "operation")
                'quantity': {
                    'value': quantity,
                    'unit': 'kg'
                },
                'observation': {
                    'quantity': detection_rate,
                    'duration': duration
                },
                'duration': {
                    'duration': duration,
                    'durationEstimationType': 'Measured'
                },
                'cause': {
                    'rootCauseAnalysis': cause_value
                } if cause_value else None,
                'source': {
                    'sourceLocation': source_name,
                    'sourceCategory': source_scale,
                    'physicalSource': source_name
                },
                'rate': detection_rate,
                'uncertainties': detection_uncertainties,
                'source_scale': source_scale,
                'source_name': source_name,
                'startTime': start_time.isoformat() if start_time else None,
                'endTime': end_time.isoformat() if end_time else None
            }
            events.append(event)
    
    return events


def merge_events_by_allen_algebra(events: List[Dict]) -> List[Dict]:
    """
    Merge overlapping events from the same source using Allen's interval algebra.
    Events from the same source that overlap or are adjacent in time are merged.
    
    Args:
        events: List of event dictionaries
    
    Returns:
        List of merged event dictionaries
    """
    if len(events) == 0:
        return []
    
    # Group events by source
    events_by_source = {}
    for event in events:
        # Use physicalSource or sourceLocation as the key
        source = event.get('source', {}).get('physicalSource', '')
        if not source:
            source = event.get('source', {}).get('sourceLocation', 'Unknown')
        if source not in events_by_source:
            events_by_source[source] = []
        events_by_source[source].append(event)
    
    merged_events = []
    
    # Process each source separately
    for source, source_events in events_by_source.items():
        # Sort events by start time
        source_events_sorted = sorted(source_events, 
                                     key=lambda x: pd.to_datetime(x.get('startTime', datetime.min)))
        
        if len(source_events_sorted) == 0:
            continue
        
        # Use a more efficient merging algorithm
        # Process events in order and merge overlapping ones
        result = [source_events_sorted[0]]
        
        for next_event in source_events_sorted[1:]:
            # Check if the last merged event overlaps with the next event
            last_event = result[-1]
            
            if can_merge_events(last_event, next_event):
                # Merge with the last event in result
                merged = merge_events(last_event, next_event)
                result[-1] = merged
            else:
                # No overlap, add as new event
                result.append(next_event)
        
        merged_events.extend(result)
    
    return merged_events


def validate_column_mapping(data: pd.DataFrame, column_mapping: Dict[str, str]) -> Dict[str, any]:
    """
    Validate that column mapping is correct and all required fields are mapped.
    
    Args:
        data: DataFrame to validate against
        column_mapping: Dictionary mapping required fields to column names
    
    Returns:
        Dictionary with validation results:
        - 'valid': bool indicating if mapping is valid
        - 'errors': list of error messages
        - 'warnings': list of warning messages
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    mandatory_fields = ['rate', 'id', 'source']
    
    # Check mandatory fields
    for field in mandatory_fields:
        mapped_col = column_mapping.get(field)
        if not mapped_col:
            result['valid'] = False
            result['errors'].append(f"Mandatory field '{field}' is not mapped")
        elif mapped_col not in data.columns:
            result['valid'] = False
            result['errors'].append(f"Column '{mapped_col}' mapped to '{field}' does not exist in data")
    
    # Check data types and constraints
    rate_col = column_mapping.get('rate')
    if rate_col and rate_col in data.columns:
        if not pd.api.types.is_numeric_dtype(data[rate_col]):
            result['errors'].append(f"Rate column '{rate_col}' must be numeric")
            result['valid'] = False
    
    # Check uncertainties column (optional)
    uncertainties_col = column_mapping.get('uncertainties')
    if uncertainties_col and uncertainties_col in data.columns:
        if not pd.api.types.is_numeric_dtype(data[uncertainties_col]):
            result['errors'].append(f"Uncertainties column '{uncertainties_col}' must be numeric")
            result['valid'] = False
    
    id_col = column_mapping.get('id')
    if id_col and id_col in data.columns:
        if data[id_col].duplicated().any():
            result['warnings'].append(f"ID column '{id_col}' contains duplicate values")
    
    # source_scale removed from UI - defaults to 'site' if not provided
    # No validation needed as it will default to 'site' in converter
    
    return result

