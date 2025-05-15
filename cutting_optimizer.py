import pandas as pd
import numpy as np
import pulp as pl
import itertools


def optimize_cutting(input_data, stock_length, cutting_gap, optimization_method="Tối Ưu Hiệu Suất Cao Nhất", stock_length_options=None, optimize_stock_length=False):
    """
    Optimizes aluminum cutting patterns to minimize waste.
    
    Args:
        input_data (DataFrame): Input data with profile codes, lengths, and quantities
        stock_length (float): Length of standard stock bars
        cutting_gap (float): Gap required between cuts
        optimization_method (str): Method to use for optimization ("Tối Ưu Hiệu Suất Cao Nhất" or "Tối Ưu Số Lượng Thanh")
        stock_length_options (list): List of available stock lengths to choose from
        optimize_stock_length (bool): Whether to optimize the stock length for each pattern
        
    Returns:
        tuple: (result_df, patterns_df, summary_df) - DataFrames with optimization results
    """
    # Use default stock length if no options provided
    if stock_length_options is None:
        stock_length_options = [stock_length]
    # Process input data to expand by quantity
    expanded_data = []
    for _, row in input_data.iterrows():
        for i in range(int(row['Quantity'])):
            expanded_data.append({
                'Profile Code': row['Profile Code'],
                'Length': row['Length'],
                'Item ID': f"{row['Profile Code']}_{i+1}"
            })
    
    expanded_df = pd.DataFrame(expanded_data)
    
    # Process each profile code separately
    profile_codes = expanded_df['Profile Code'].unique()
    all_patterns = []
    all_summaries = []
    all_results = []
    
    for profile_code in profile_codes:
        # Filter data for this profile
        profile_data = expanded_df[expanded_df['Profile Code'] == profile_code].copy()
        
        # Get the lengths needed for this profile
        lengths = profile_data['Length'].values
        
        # Sort lengths in descending order for better initial heuristic
        lengths = np.sort(lengths)[::-1]
        
        # Store best patterns across all stock lengths
        best_patterns = []
        best_remaining_lengths = []
        best_stock_length = stock_length
        best_efficiency = 0
        best_bar_count = float('inf')
        
        # Try different stock lengths if optimization is enabled
        for current_stock_length in stock_length_options:
            # First-fit decreasing heuristic to generate initial patterns
            patterns = []
            remaining_lengths = []
            
            for length in lengths:
                added = False
                
                # Try to add to existing patterns
                for i, remaining in enumerate(remaining_lengths):
                    if length <= remaining:
                        # Update the pattern
                        patterns[i].append(length)
                        # Update remaining length (subtract length and cutting gap)
                        remaining_lengths[i] = remaining - length - cutting_gap
                        added = True
                        break
                
                # If couldn't add to existing patterns, create a new pattern
                if not added:
                    patterns.append([length])
                    remaining_lengths.append(current_stock_length - length - cutting_gap)
            
            # Calculate metrics for this stock length
            total_used_length = sum(sum(pattern) for pattern in patterns)
            total_stock_length = current_stock_length * len(patterns)
            current_efficiency = total_used_length / total_stock_length if total_stock_length > 0 else 0
            
            # Determine if this is the best solution based on optimization method
            if optimization_method == "Tối Ưu Hiệu Suất Cao Nhất":
                # If optimizing for efficiency, pick the highest efficiency
                if current_efficiency > best_efficiency:
                    best_patterns = patterns
                    best_remaining_lengths = remaining_lengths
                    best_stock_length = current_stock_length
                    best_efficiency = current_efficiency
                    best_bar_count = len(patterns)
            else:  # "Tối Ưu Số Lượng Thanh"
                # If optimizing for bar count, pick the lowest count (or highest efficiency if tied)
                if len(patterns) < best_bar_count or (len(patterns) == best_bar_count and current_efficiency > best_efficiency):
                    best_patterns = patterns
                    best_remaining_lengths = remaining_lengths
                    best_stock_length = current_stock_length
                    best_efficiency = current_efficiency
                    best_bar_count = len(patterns)
        
        # Use the best solution found
        patterns = best_patterns
        remaining_lengths = best_remaining_lengths
        current_stock_length = best_stock_length
        
        # Create patterns DataFrame
        pattern_data = []
        bar_number = 1
        
        for pattern, remaining in zip(patterns, remaining_lengths):
            # Calculate total used length including cutting gaps
            used_length = current_stock_length - remaining
            # Calculate efficiency
            efficiency = (sum(pattern) / current_stock_length)
            
            pattern_data.append({
                'Profile Code': profile_code,
                'Bar Number': bar_number,
                'Stock Length': current_stock_length,
                'Used Length': used_length,
                'Remaining Length': remaining,
                'Efficiency': efficiency,
                'Cutting Pattern': '+'.join(str(p) for p in pattern),
                'Pieces': len(pattern)
            })
            
            # Update result data for each piece in the pattern
            for length in pattern:
                # Find the first unassigned item of this length
                unassigned_items = profile_data[(profile_data['Length'] == length) & 
                                       (~profile_data['Item ID'].isin([r.get('Item ID') for r in all_results]))]
                
                if not unassigned_items.empty:
                    item_idx = unassigned_items.index[0]
                    
                    all_results.append({
                        'Profile Code': profile_code,
                        'Item ID': profile_data.loc[item_idx, 'Item ID'],
                        'Length': length,
                        'Bar Number': bar_number
                    })
            
            bar_number += 1
        
        all_patterns.extend(pattern_data)
        
        # Create summary for this profile
        total_bars = len(patterns)
        total_length_needed = sum(lengths)
        total_length_used = sum(pattern['Stock Length'] for pattern in pattern_data)
        avg_efficiency = np.mean([p['Efficiency'] for p in pattern_data])
        
        all_summaries.append({
            'Profile Code': profile_code,
            'Total Pieces': len(lengths),
            'Total Bars Used': total_bars,
            'Total Length Needed (mm)': total_length_needed,
            'Total Stock Length (mm)': total_length_used,
            'Waste (mm)': total_length_used - total_length_needed - (len(lengths) - total_bars) * cutting_gap,
            'Overall Efficiency': total_length_needed / total_length_used,
            'Average Bar Efficiency': avg_efficiency
        })
    
    # Convert to DataFrames
    patterns_df = pd.DataFrame(all_patterns)
    summary_df = pd.DataFrame(all_summaries)
    result_df = pd.DataFrame(all_results)
    
    # Sort and clean up DataFrames
    if not patterns_df.empty:
        patterns_df = patterns_df.sort_values(['Profile Code', 'Bar Number']).reset_index(drop=True)
        # Format the efficiency as percentage
        patterns_df['Efficiency'] = patterns_df['Efficiency'].round(4)
    
    if not summary_df.empty:
        summary_df = summary_df.sort_values('Profile Code').reset_index(drop=True)
        # Format the efficiency as percentage
        summary_df['Overall Efficiency'] = summary_df['Overall Efficiency'].round(4)
        summary_df['Average Bar Efficiency'] = summary_df['Average Bar Efficiency'].round(4)
    
    if not result_df.empty:
        result_df = result_df.sort_values(['Profile Code', 'Bar Number']).reset_index(drop=True)
    
    return result_df, patterns_df, summary_df
