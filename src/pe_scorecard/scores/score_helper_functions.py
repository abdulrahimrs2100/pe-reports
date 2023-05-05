"""A file containing the helper functions for various scoring algorithms."""
# Standard Python Libraries
import calendar
import math

# Third-Party Libraries
import pandas as pd
from dateutil.relativedelta import relativedelta


# Add skewness function?


def rescale(values, width, offset):
    """
    Rescale Pandas Series of values to the specified width and offset.

    Args:
        values: Pandas Series of values that you want to rescale
        width: The new width of the rescaled values
        offset: The new starting point of the rescaled values
            examples:
            width = 42, offset = 5 results in values from 5-47
            width = 100, offset = -3 results in values from -3-97
    Returns:
        A Pandas Series of the new, re-scaled values
    """
    # Get min/max values
    min_val = values.min()
    max_val = values.max()
    # Catch edge case
    if min_val == max_val:
        # If all the same number, just return all zeros
        return pd.Series([0] * values.size)
    else:
        # Otherwise, rescale 0-100
        values = ((values - min_val) / (max_val - min_val) * width) + offset
        return values


def get_prev_startstop(curr_date, num_periods):
    """
    Get the start/stop dates for the specified number of preceding report periods, given the current date.
    i.e. If curr_date = 2022-08-15 and num_periods = 3, it'll return: [[7/1, 7/15], [7/16, 7/31], [8/1, 8/15]]
    Args:
        curr_date: current report period date (i.e. 2022-08-15)
        num_periods: number of preceding report periods to calculate (i.e. 15)
    Returns:
        The start and stop dates for the specified number or report periods preceding the current date
    """
    # Array to hold start/stop dates
    start_stops = []
    month_diff = []
    # Calculating month difference array
    for n in range(0, math.ceil(num_periods / 2) + 1):
        month_diff.append(n)
        month_diff.append(n)
    # Calculate start/stop dates
    if curr_date.day == 15:
        month_diff = month_diff[1 : num_periods + 1]
        for i in range(0, num_periods):
            if (i % 2) == 0:
                # Even idx 1 - 15
                start_date = (curr_date + relativedelta(months=-month_diff[i])).replace(
                    day=1
                )
                end_date = curr_date + relativedelta(months=-month_diff[i])
                start_stops.insert(0, [start_date.date(), end_date.date()])
            else:
                # odd idx 16 - 30/31
                start_date = (curr_date + relativedelta(months=-month_diff[i])).replace(
                    day=16
                )
                end_date = curr_date + relativedelta(months=-month_diff[i])
                end_date = end_date.replace(
                    day=calendar.monthrange(end_date.year, end_date.month)[1]
                )
                start_stops.insert(0, [start_date.date(), end_date.date()])
    else:
        month_diff = month_diff[:num_periods]
        for i in range(0, num_periods):
            if (i % 2) == 0:
                # Even idx 16 - 30/31
                start_date = (curr_date + relativedelta(months=-month_diff[i])).replace(
                    day=16
                )
                end_date = curr_date + relativedelta(months=-month_diff[i])
                end_date = end_date.replace(
                    day=calendar.monthrange(end_date.year, end_date.month)[1]
                )
                start_stops.insert(0, [start_date.date(), end_date.date()])
            else:
                # odd idx 1 - 15
                start_date = (curr_date + relativedelta(months=-month_diff[i])).replace(
                    day=1
                )
                end_date = (curr_date + relativedelta(months=-month_diff[i])).replace(
                    day=15
                )
                start_stops.insert(0, [start_date.date(), end_date.date()])
    # Return 2D list of start/stop dates
    return start_stops