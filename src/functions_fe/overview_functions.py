import pandas as pd 
import numpy as np 
from scipy import stats


# ----------------------------------------------------------------------------
# Helper function - safely extract annual emissions
# ----------------------------------------------------------------------------
def get_annual_emissions(country_df):
    """Safely extract annual emissions from dataframe"""
    
    # Try different possible column patterns
    year_cols = []
    
    # Pattern 1: gfw_forest_carbon_gross_emissions_2001__Mg_CO2e
    pattern1 = [c for c in country_df.columns if c.startswith('gfw_forest_carbon_gross_emissions_') and c.endswith('__Mg_CO2e')]
    if pattern1:
        year_cols = pattern1
    else:
        # Pattern 2: gfw_forest_carbon_gross_emissions_2001_Mg_CO2e (without double underscore)
        pattern2 = [c for c in country_df.columns if c.startswith('gfw_forest_carbon_gross_emissions_') and 'Mg_CO2e' in c]
        if pattern2:
            year_cols = pattern2
        else:
            # Pattern 3: Any column with emissions and a year
            import re
            pattern3 = [c for c in country_df.columns if 'emissions' in c.lower() and re.search(r'20\d{2}', c)]
            if pattern3:
                year_cols = pattern3
    
    years, annual = [], []
    for c in year_cols:
        try:
            # Try different extraction methods
            year = None
            
            # Method 1: split by underscore
            parts = c.split('_')
            for part in parts:
                if part.isdigit() and len(part) == 4 and part.startswith('20'):
                    year = int(part)
                    break
            
            # Method 2: regex if method 1 failed
            if year is None:
                import re
                match = re.search(r'20\d{2}', c)
                if match:
                    year = int(match.group())
            
            if year is not None:
                years.append(year)
                annual.append(country_df[c].sum())
        except (ValueError, IndexError):
            continue
    
    # Sort by year
    if years and annual:
        sorted_data = sorted(zip(years, annual))
        years, annual = zip(*sorted_data)
        return list(years), list(annual)
    
    return [], []


# ----------------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------------
def forest_metrics(country_df):
    """Calculate comprehensive forest metrics for a country"""
    
    # Overall country statistics
    metrics = {
        'total_area': country_df['umd_tree_cover_extent_2000__ha'].sum(),
        'total_carbon': country_df['gfw_aboveground_carbon_stocks_2000__Mg_C'].sum(),
        'avg_carbon_density': country_df['avg_gfw_aboveground_carbon_stocks_2000__Mg_C_ha-1'].mean(),
        'total_emissions': country_df['gfw_forest_carbon_gross_emissions__Mg_CO2e_yr-1'].sum(),
        'total_removals': country_df['gfw_forest_carbon_gross_removals__Mg_CO2_yr-1'].sum(),
        'net_flux': country_df['gfw_forest_carbon_net_flux__Mg_CO2e_yr-1'].sum(),
        'n_regions': len(country_df['subnational1'].unique())
    }

    # Calculate regional contribution to emissions
    regional_emissions = country_df.groupby('subnational1')['gfw_forest_carbon_gross_emissions__Mg_CO2e_yr-1'].sum()
    if not regional_emissions.empty and metrics['total_emissions'] > 0:
        metrics['top_emitting_region'] = regional_emissions.idxmax()
        metrics['top_region_share'] = (regional_emissions.max() / metrics['total_emissions']) * 100
    else:
        metrics['top_emitting_region'] = None
        metrics['top_region_share'] = 0

    # Calculate trends using safe extraction
    years, annual_emissions = get_annual_emissions(country_df)
    
    if len(annual_emissions) > 1:
        slope, intercept, r_value, p_value, std_err = stats.linregress(range(len(annual_emissions)), annual_emissions)
        metrics['trend_slope'] = slope
        metrics['trend_p_value'] = p_value
        metrics['trend_significant'] = p_value < 0.05
        metrics['emissions_increasing'] = slope > 0
    else:
        metrics['trend_slope'] = 0
        metrics['trend_p_value'] = 1.0
        metrics['trend_significant'] = False
        metrics['emissions_increasing'] = False
    
    return metrics


# ----------------------------------------------------------------------------
# Deforestation hotspots
# ----------------------------------------------------------------------------
def detect_deforestation_hotspots(country_df, top_n=5):
    """Identify regions with highest deforestation pressure"""
    
    # Create a copy to avoid SettingWithCopyWarning
    df = country_df.copy()
    
    # Calculate key pressure indicators
    # Convert emissions from CO₂e to C (divide by 3.67)
    # Then calculate loss rate as % of carbon stock
    df.loc[:, 'pressure_score'] = (
        (df['gfw_forest_carbon_gross_emissions__Mg_CO2e_yr-1'] / 3.67) / 
        df['gfw_aboveground_carbon_stocks_2000__Mg_C']
    ) * 100  # % of carbon stock lost annually
    
    # Replace inf/NaN with 0
    df.loc[:, 'pressure_score'] = df['pressure_score'].replace([np.inf, -np.inf], 0).fillna(0)
    
    # Get top hotspots
    hotspots = df.nlargest(top_n, 'pressure_score')[['subnational1', 'pressure_score', 'gfw_forest_carbon_gross_emissions__Mg_CO2e_yr-1']]
    
    return hotspots


# ----------------------------------------------------------------------------
# Carbon Forecast
# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------
# Carbon Forecast
# ----------------------------------------------------------------------------
def carbon_forecast(country_df, years_ahead=5):
    """Generate simple linear forecast of emissions"""
    
    # Safely extract years and emissions
    years, annual_emissions = get_annual_emissions(country_df)
    
    # Need at least 3 data points for a meaningful forecast
    if len(annual_emissions) >= 3:
        try:
            # Convert to numpy arrays
            years_arr = np.array(years)
            emissions_arr = np.array(annual_emissions)
            
            # Calculate linear regression
            slope, intercept = np.polyfit(years_arr, emissions_arr, 1)
            
            # Generate forecast
            future_years = list(range(int(max(years)) + 1, int(max(years)) + years_ahead + 1))
            forecast_values = [slope * year + intercept for year in future_years]
            
            # Calculate confidence interval (simplified)
            # Get predictions for historical years
            historical_predictions = [slope * year + intercept for year in years]
            residuals = emissions_arr - np.array(historical_predictions)
            std_err = np.std(residuals)
            
            # 95% confidence interval
            ci = 1.96 * std_err * np.sqrt(1 + 1/len(years))
            
            return pd.DataFrame({
                'year': future_years,
                'forecast_emissions': forecast_values,
                'confidence_interval': [ci] * len(future_years)
            })
        except Exception as e:
            print(f"Forecast error: {e}")
            return None
    else:
        # Not enough data points
        return None