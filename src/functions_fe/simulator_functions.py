# FUNCTIONS TO BE USED IN THE SIMULATOR 
import numpy as np

# Avoid overlapping regions labels
def min_pairwise_distance(regions_lat, regions_lon):

    n = len(regions_lon)
    if n < 2:
        return None

    mean_lat = np.mean(regions_lat)
    cos_lat = np.cos(np.radians(mean_lat))

    min_dist = np.inf
    for i in range(n):
        for j in range(i+1, n):
            dlon = (regions_lon[i] - regions_lon[j]) * cos_lat
            dlat = regions_lat[i]- regions_lat[j]
            dist = np.sqrt(dlon**2+dlat**2)
            if dist < min_dist:
                min_dist = dist

    return min_dist


# Scale of regions label adjusting with zoom
def compute_zoom_scale(regions_lon, regions_lat, min_scale=1.3, max_scale=9.0, padding=1.3):

    if not regions_lon or not regions_lat or len(regions_lon) < 2:
        return 4.0

    lon_span = max(regions_lon) - min(regions_lon)
    lat_span = max(regions_lat) - min(regions_lat)
    mean_lat = np.mean(regions_lat)
    lon_span_adjusted = lon_span * np.cos(np.radians(mean_lat))

    fit_span = max(lon_span_adjusted, lat_span, 0.5) * padding
    scale_fit = 40.0 / fit_span

    nn_dist = min_pairwise_distance(regions_lon, regions_lat)
    scale_separate = (6.0 / nn_dist) if nn_dist and nn_dist > 0 else scale_fit

    scale = max(scale_fit, scale_separate)
    res = float(np.clip(scale, min_scale, max_scale))

    return res

# Reduce size of label as number of regions increases (avoid overlap)
def region_label_fontsize(n_regions, base_size=13, min_size=8):
    
    size = base_size-(n_regions // 6)
    top = max(size, min_size)
    
    return top

# Drop any region if coordinates invalid
def filter_valid_coordinates(names, lons, lats):
    
    clean_names, clean_lons, clean_lats = [], [], []
    dropped = []

    for name, lon, lat in zip(names, lons, lats):
        try:
            lon_f, lat_f = float(lon), float(lat)
        except (TypeError, ValueError):
            dropped.append(name)
            continue

        if np.isfinite(lon_f) and np.isfinite(lat_f):
            clean_names.append(name)
            clean_lats.append(lat_f)
            clean_lons.append(lon_f)
        else:
            dropped.append(name)
    
    return clean_names, clean_lons, clean_lats, dropped


# Build circle around region centroid (use cos lat to adjust to sphere)
def generate_circle_coords(center_lon, center_lat, radius_deg, n_points=48):

    cos_lat = np.cos(np.radians(center_lat))
    cos_lat = cos_lat if abs(cos_lat) > 1e-6 else 1e-6

    thetas = np.linspace(0,2 * np.pi, n_points)
    lons = center_lon + (radius_deg / cos_lat) * np.cos(thetas)
    lats = center_lat + radius_deg * np.sin(thetas)
    lons = lons.tolist()
    lats = lats.tolist()

    return lons, lats

# Adjust size of the circle around region to avoid overlapping 
def build_region_circle_traces_data(regions_lon, regions_lat, min_radius=0.15, max_radius=2.5, shrink_factor=0.4):

    n = len(regions_lon)
    all_lons, all_lats = [], []

    for i in range(n):
        if n > 1:
            cos_lat = np.cos(np.radians(regions_lat[i]))
            nearest = min(
                np.sqrt(((regions_lon[i] - regions_lon[j]) * cos_lat) ** 2 +
                         (regions_lat[i] - regions_lat[j]) ** 2)
                for j in range(n) if j != i
            )
            radius = np.clip(nearest * shrink_factor, min_radius, max_radius)
        else:
            radius = min_radius

        circ_lon, circ_lat = generate_circle_coords(regions_lon[i], regions_lat[i], radius)
        all_lons.extend(circ_lon)
        all_lats.extend(circ_lat)
        all_lons.append(None)
        all_lats.append(None)

    return all_lons, all_lats


# Scale plant marker size to its emissions
def emission_to_marker_size(emissions, all_emissions, min_size=6, max_size=22):
    
    if not all_emissions or max(all_emissions) <= 0:
        return (min_size + max_size) / 2

    log_vals = np.log10(np.clip(all_emissions, 1e-6, None))
    lo, hi = log_vals.min(), log_vals.max()

    if hi - lo < 1e-9:
        return (min_size + max_size) / 2

    log_e = np.log10(max(emissions, 1e-6))
    t = (log_e - lo) / (hi - lo)

    size = min_size + t * (max_size - min_size)

    return size

# Summary sector statistics
def get_sector_summary(country, sector, plants):

    if not plants:
        return None
    
    total_emissions = sum(p['emissions'] for p in plants)
    num_plants = len(plants)
    avg_emissions = total_emissions / num_plants if num_plants > 0 else 0
    max_emissions = max(p['emissions'] for p in plants) if plants else 0
    min_emissions = min(p['emissions'] for p in plants) if plants else 0
    
    summary = {
        'total_emissions': total_emissions,
        'num_plants': num_plants,
        'avg_emissions': avg_emissions,
        'max_emissions': max_emissions,
        'min_emissions': min_emissions,
    }

    return summary