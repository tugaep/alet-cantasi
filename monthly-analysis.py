import pandas as pd
import glob
import os
import argparse
import calendar
from datetime import datetime, timedelta
import numpy as np

""" created for monthly analysis of given distruted data on many files.

    you ca analyzie the previous month data by default. 
    if you specify the focused columns, you can analyze the data of the specified columns.

    7.10.2025: initial version
    tugaep

"""


def get_target_period(today=None, year=None, month=None):
    """
   return the start and end date of the target period

    """
    if today is None:
        today = datetime.now()
    
    #manual year and month is provided
    if year is not None and month is not None:
        target_year = year
        target_month = month
    else:
        # automatic: previous month
        # if january, go to the previous year's december
        if today.month == 1:
            target_year = today.year - 1
            target_month = 12
        else:
            target_year = today.year
            target_month = today.month - 1
    
    
    last_day = calendar.monthrange(target_year, target_month)[1]
    
    
    start_date = datetime(target_year, target_month, 1)
    end_date = datetime(target_year, target_month, last_day)
    
    
    month_name = calendar.month_name[target_month]
    
    return start_date, end_date, target_year, target_month, month_name


def load_weeks(input_glob, required_columns=[]):
    """
    find the files that match the given glob pattern and return a list of DataFrames
    """
    files = glob.glob(input_glob)
    if not files:
        print(f"warning: no files found for the given glob pattern: '{input_glob}'")
        return []
    
    print(f"found files: {files}")
    
    loaded_data = []
    for file in files:
        try:
            
            sample_df = pd.read_csv(file, nrows=1)
            
          
            df = pd.read_csv(file, usecols=required_columns)
            loaded_data.append((file, df))
            
        except Exception as e:
            print(f"error: while loading the file {file}: {e}")
            continue
    
    return loaded_data


def normalize_columns(df):
    """
    standardize the column names of the DataFrame
    """
    df = df.rename(columns={
        'Start Date': 'STARTDATE',
        'End Date': 'ENDDATE'
    })
    
    
    df['STARTDATE'] = pd.to_datetime(df['STARTDATE'], errors='coerce')
    df['ENDDATE'] = pd.to_datetime(df['ENDDATE'], errors='coerce')
    
    # clean invalid dates
    df = df.dropna(subset=['STARTDATE', 'ENDDATE'])
    
    return df


def filter_by_period(df, start_date, end_date):
    """
    filter the df by the given date range
    """
    return df[(df['STARTDATE'] >= start_date) & (df['STARTDATE'] <= end_date)]



def interactive_mode():
    """
    get the year and month from the user
    """
    print("\n" + "="*60)
    print("interactive mode - select the year and month")
    print("="*60)
    
    try:
        year_input = input("\nenter the year to analyze (e.g. 2025, leave blank for automatic previous month): ").strip()
        
        if not year_input:
            print("automatic mode selected (previous month).")
            return None, None
        
        year = int(year_input)
        
        month_input = input("enter the month to analyze (1-12): ").strip()
        month = int(month_input)
        
        if month < 1 or month > 12:
            print("error: month should be between 1 and 12")
            return None, None
        
        print(f"\nthe selected period: {calendar.month_name[month]} {year}")
        return year, month
                
    except ValueError:
        print("error: invalid input")
        return None, None


def main():
    """main function - handle the CLI arguments and run the analysis"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        """
    )
    
    parser.add_argument('--year', type=int, help='the year to analyze (e.g. 2025)')
    parser.add_argument('--month', type=int, help='the month to analyze (1-12)')
    parser.add_argument('--interactive', '-i', action='store_true', 
                       help='interactive mode - select the year and month')
    parser.add_argument('--input-glob', default='nyc_week*.csv',
                       help='input files glob pattern (default: nyc_week*.csv)')
    parser.add_argument('--city', default='nyc',
                       help='city name (default: nyc)')
    parser.add_argument('--output-dir', default='.',
                       help='output directory (default: current directory)')
    
    args = parser.parse_args()
    
   
    if args.interactive:
        year, month = interactive_mode()
        if year is None and month is None and not args.year and not args.month:
           
            pass
        elif year is not None and month is not None:
            args.year = year
            args.month = month
        else:
            print("interactive mode cancelled, exiting.")
            return
    
    
    if (args.year is not None and args.month is None) or (args.year is None and args.month is not None):
        print("error: --year and --month must be used together")
        parser.print_help()
        return
    
    if args.month is not None and (args.month < 1 or args.month > 12):
        print("error: month should be between 1 and 12")
        return
    
  
    start_date, end_date, year, month, month_name = get_target_period(
        year=args.year, 
        month=args.month
    )
    
   
    analyze_data(
        input_glob=args.input_glob,
        start_date=start_date,
        end_date=end_date,
        year=year,
        month=month,
        month_name=month_name,
        city=args.city,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()
