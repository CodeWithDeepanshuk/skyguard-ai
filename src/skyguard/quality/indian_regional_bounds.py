"""Indian Regional Climatological and Physical Parameter Boundaries.

Provides verified, meteorologically authentic physical limits across India's
climatic zones for:
- Air Temperature (°C)
- Barometric / Sea-Level Pressure (hPa)
- Relative Humidity (%)

References:
- India Meteorological Department (IMD) National Data Centre (NDC) Pune climate normals
- WMO-No. 8: Guide to Meteorological Instruments and Methods of Observation
- Historical recorded extremes across Indian meteorological stations:
  * Extreme low: -45.0°C (Dras, Ladakh)
  * Extreme high: +51.0°C (Phalodi, Rajasthan) / +52.3°C (Mungeshpur AWS check)
  * Extreme low pressure: 912–960 hPa (Bay of Bengal Super Cyclones)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class RegionalBounds:
    zone_name: str
    temp_min_c: float
    temp_max_c: float
    mslp_min_hpa: float
    mslp_max_hpa: float
    station_pressure_min_hpa: float
    station_pressure_max_hpa: float
    humidity_min_pct: float
    humidity_max_pct: float
    coastal: bool = False
    high_altitude: bool = False
    description: str = ""


# Verified physical boundaries for India's 8 official climatic zones
INDIAN_CLIMATE_BOUNDS: Dict[str, RegionalBounds] = {
    "Northern Himalayas": RegionalBounds(
        zone_name="Northern Himalayas",
        temp_min_c=-45.0,  # Dras, Kargil, Leh, Gulmarg winter cold waves
        temp_max_c=36.0,   # Summer valleys (Dehradun, Jammu, valley heat)
        mslp_min_hpa=970.0,
        mslp_max_hpa=1045.0,
        station_pressure_min_hpa=450.0,  # At 3,000m-4,500m ASL station pressure is 500-700 hPa
        station_pressure_max_hpa=960.0,
        humidity_min_pct=5.0,
        humidity_max_pct=100.0,
        high_altitude=True,
        description="Alpine/Montane Himalayan region (Ladakh, J&K, HP, Uttarakhand)",
    ),
    "Western Arid/Semi-Arid": RegionalBounds(
        zone_name="Western Arid/Semi-Arid",
        temp_min_c=-3.0,   # Sikar/Churu winter radiation frost
        temp_max_c=52.5,   # Phalodi/Churu extreme heat record (51.0°C recorded)
        mslp_min_hpa=980.0,
        mslp_max_hpa=1035.0,
        station_pressure_min_hpa=910.0,
        station_pressure_max_hpa=1035.0,
        humidity_min_pct=3.0,  # Extreme pre-monsoon dry air (May/June afternoons)
        humidity_max_pct=100.0,
        description="Thar Desert and arid northwest (Rajasthan, Kutch, North Gujarat)",
    ),
    "Indo-Gangetic Plains": RegionalBounds(
        zone_name="Indo-Gangetic Plains",
        temp_min_c=-1.0,   # Severe winter cold waves with dense advection fog
        temp_max_c=49.5,   # Severe summer pre-monsoon heatwaves (Delhi, UP, Bihar)
        mslp_min_hpa=982.0,
        mslp_max_hpa=1034.0,
        station_pressure_min_hpa=930.0,
        station_pressure_max_hpa=1034.0,
        humidity_min_pct=8.0,
        humidity_max_pct=100.0,
        description="Fertile northern plains (Delhi, Punjab, Haryana, UP, Bihar, WB)",
    ),
    "Central Plateau": RegionalBounds(
        zone_name="Central Plateau",
        temp_min_c=4.0,    # Central plateau winter minimums
        temp_max_c=48.5,   # Vidarbha / MP pre-monsoon heatwaves
        mslp_min_hpa=980.0,
        mslp_max_hpa=1030.0,
        station_pressure_min_hpa=880.0,
        station_pressure_max_hpa=1028.0,
        humidity_min_pct=8.0,
        humidity_max_pct=98.0,
        description="Central inland plateau (Madhya Pradesh, Chhattisgarh, Vidarbha)",
    ),
    "Deccan Plateau": RegionalBounds(
        zone_name="Deccan Plateau",
        temp_min_c=6.0,    # Bangalore, Hyderabad, interior Karnataka winter night
        temp_max_c=46.5,   # Rayalaseema, Telangana summer maximum
        mslp_min_hpa=982.0,
        mslp_max_hpa=1028.0,
        station_pressure_min_hpa=860.0,  # Elevated plateau (Bangalore ~920m ASL, ~910 hPa)
        station_pressure_max_hpa=1026.0,
        humidity_min_pct=10.0,
        humidity_max_pct=98.0,
        description="Peninsular interior plateau (Karnataka, Telangana, Rayalaseema)",
    ),
    "Coastal Plains": RegionalBounds(
        zone_name="Coastal Plains",
        temp_min_c=12.0,   # Coastal winter minimums (maritime moderation prevents freeze)
        temp_max_c=43.0,   # Sea breeze typically caps temperatures below 42°C
        mslp_min_hpa=950.0,  # Tropical cyclones and severe deep depressions
        mslp_max_hpa=1026.0,
        station_pressure_min_hpa=940.0,
        station_pressure_max_hpa=1026.0,
        humidity_min_pct=28.0,  # Maritime moisture buffer
        humidity_max_pct=100.0,
        coastal=True,
        description="Maritime coastal belt (Konkan, Malabar, Coromandel, Odisha coast)",
    ),
    "Northeast Hills": RegionalBounds(
        zone_name="Northeast Hills",
        temp_min_c=0.0,    # Shillong / Tawang lower valleys winter
        temp_max_c=39.0,   # Brahmaputra valley summer
        mslp_min_hpa=975.0,
        mslp_max_hpa=1030.0,
        station_pressure_min_hpa=750.0,  # Shillong/Meghalaya plateau (1500m ASL)
        station_pressure_max_hpa=1030.0,
        humidity_min_pct=20.0,
        humidity_max_pct=100.0,
        description="Northeastern hill states (Assam, Meghalaya, Arunachal, Nagaland)",
    ),
    "Island Territories": RegionalBounds(
        zone_name="Island Territories",
        temp_min_c=18.0,   # Tropical oceanic maritime stability
        temp_max_c=36.0,
        mslp_min_hpa=950.0,  # Cyclones in Bay of Bengal / Arabian Sea
        mslp_max_hpa=1022.0,
        station_pressure_min_hpa=950.0,
        station_pressure_max_hpa=1022.0,
        humidity_min_pct=45.0,
        humidity_max_pct=100.0,
        coastal=True,
        description="Oceanic islands (Andaman & Nicobar, Lakshadweep)",
    ),
}

# Fallback national physical envelope
NATIONAL_PHYSICAL_ENVELOPE = RegionalBounds(
    zone_name="India National Envelope",
    temp_min_c=-45.0,
    temp_max_c=53.0,
    mslp_min_hpa=945.0,
    mslp_max_hpa=1045.0,
    station_pressure_min_hpa=450.0,
    station_pressure_max_hpa=1045.0,
    humidity_min_pct=2.0,
    humidity_max_pct=100.0,
    description="All-India extreme physical limits",
)


def is_coastal_location(lat: float, lon: float, state: str = "", district: str = "") -> bool:
    """Determine if geographic coordinates or station metadata place it in a coastal zone."""
    text = f"{state} {district}".lower()
    coastal_keywords = [
        "mumbai", "konkan", "goa", "ratnagiri", "thane", "palghar", "raigad",
        "chennai", "coastal", "malabar", "kochi", "trivandrum", "thiruvananthapuram",
        "alappuzha", "kannur", "kozhikode", "puri", "paradip", "balasore", "gopalpur",
        "visakhapatnam", "vizag", "machilipatnam", "kakinada", "nellore",
        "mangaluru", "mangalore", "udupi", "karwar", "digha", "sundarbans",
        "kandla", "porbandar", "veraval", "bhavnagar", "surat",
    ]
    if any(k in text for k in coastal_keywords):
        return True

    # Coordinate boundaries for Indian coastline within ~40 km of sea
    # West Coast (Arabian Sea)
    if 8.0 <= lat <= 20.5 and 72.0 <= lon <= 74.0:
        return True
    if 20.5 <= lat <= 23.5 and 68.5 <= lon <= 73.0:  # Gujarat coast
        return True
    # East Coast (Bay of Bengal)
    if 8.0 <= lat <= 14.0 and 78.5 <= lon <= 80.5:   # Tamil Nadu coast
        return True
    if 14.0 <= lat <= 19.5 and 80.0 <= lon <= 85.5:  # Andhra coast
        return True
    if 19.5 <= lat <= 22.0 and 84.5 <= lon <= 89.0:  # Odisha/Bengal coast
        return True
    return False


def classify_indian_region(
    lat: float,
    lon: float,
    elev_m: float = 0.0,
    state: str = "",
    climate_zone_hint: str = "",
) -> RegionalBounds:
    """Classify station into its appropriate regional bounds profile."""
    # 1. Direct hint match
    if climate_zone_hint and climate_zone_hint in INDIAN_CLIMATE_BOUNDS:
        return INDIAN_CLIMATE_BOUNDS[climate_zone_hint]

    # Normalize state string
    st_clean = (state or "").strip().lower()

    # 2. Island territories
    if (lat < 14.0 and lon > 92.0) or (lat < 12.0 and lon < 74.0 and "lakshadweep" in st_clean):
        return INDIAN_CLIMATE_BOUNDS["Island Territories"]

    # 3. High Himalayas
    if lat >= 30.5 or (lat >= 28.5 and elev_m > 1200.0) or any(s in st_clean for s in ["ladakh", "jammu", "kashmir", "himachal", "uttarakhand"]):
        if elev_m > 1200.0 or lat >= 31.0:
            return INDIAN_CLIMATE_BOUNDS["Northern Himalayas"]

    # 4. Northeast Hills
    if (lon > 88.5 and lat > 21.5) or any(s in st_clean for s in ["assam", "meghalaya", "arunachal", "nagaland", "manipur", "mizoram", "tripura"]):
        return INDIAN_CLIMATE_BOUNDS["Northeast Hills"]

    # 5. Coastal Plains
    if is_coastal_location(lat, lon, state):
        return INDIAN_CLIMATE_BOUNDS["Coastal Plains"]

    # 6. Western Arid / Semi-Arid (Thar)
    if (lon < 75.5 and 22.0 <= lat <= 30.0) or "rajasthan" in st_clean:
        return INDIAN_CLIMATE_BOUNDS["Western Arid/Semi-Arid"]

    # 7. Indo-Gangetic Plains
    if (24.0 <= lat <= 30.5 and 75.5 <= lon <= 88.5) or any(s in st_clean for s in ["delhi", "punjab", "haryana", "uttar pradesh", "bihar"]):
        return INDIAN_CLIMATE_BOUNDS["Indo-Gangetic Plains"]

    # 8. Deccan Plateau (Peninsular South Interior)
    if (12.0 <= lat < 20.0 and 74.0 <= lon <= 80.0) or any(s in st_clean for s in ["karnataka", "telangana", "rayalaseema"]):
        return INDIAN_CLIMATE_BOUNDS["Deccan Plateau"]

    # 9. Central Plateau
    return INDIAN_CLIMATE_BOUNDS.get("Central Plateau", NATIONAL_PHYSICAL_ENVELOPE)


def check_regional_physical_bounds(
    temperature_c: Optional[float],
    pressure_hpa: Optional[float],
    humidity_pct: Optional[float],
    bounds: RegionalBounds,
    elevation_m: float = 0.0,
    is_mslp: bool = False,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Check if observation parameters fall strictly within regional physical bounds.
    
    Returns:
        (is_valid, parameter_violated, explanation_string)
    """
    # 1. Temperature check
    if temperature_c is not None and not math.isnan(temperature_c):
        if temperature_c < bounds.temp_min_c or temperature_c > bounds.temp_max_c:
            return (
                False,
                "temperature",
                f"Observed temperature {temperature_c:.1f}°C is physically impossible for {bounds.zone_name} (valid range: [{bounds.temp_min_c:.1f}°C to {bounds.temp_max_c:.1f}°C]).",
            )

    # 2. Relative Humidity check
    if humidity_pct is not None and not math.isnan(humidity_pct):
        if humidity_pct < bounds.humidity_min_pct or humidity_pct > bounds.humidity_max_pct:
            return (
                False,
                "humidity",
                f"Observed relative humidity {humidity_pct:.0f}% violates physical limits for {bounds.zone_name} (valid range: [{bounds.humidity_min_pct:.0f}% to {bounds.humidity_max_pct:.0f}%]).",
            )

    # 3. Pressure check (elevation aware)
    if pressure_hpa is not None and not math.isnan(pressure_hpa):
        if is_mslp or abs(elevation_m) < 30.0:
            p_min, p_max = bounds.mslp_min_hpa, bounds.mslp_max_hpa
            label = "MSLP"
        else:
            # Approximate expected station pressure given elevation
            # Standard barometric reduction: P ~ 1013.25 * (1 - 2.25577e-5 * h)^5.25588
            dh = max(0.0, elevation_m)
            expected_p_at_elev = 1013.25 * math.pow(max(0.1, 1.0 - 2.25577e-5 * dh), 5.25588)
            p_min = max(350.0, expected_p_at_elev - 60.0)
            p_max = min(1085.0, expected_p_at_elev + 60.0)
            label = f"Station Pressure at {elevation_m:.0f}m ASL"

        if pressure_hpa < p_min or pressure_hpa > p_max:
            return (
                False,
                "pressure",
                f"Observed barometric pressure {pressure_hpa:.1f} hPa is outside physical bounds for {label} in {bounds.zone_name} (valid range: [{p_min:.1f} to {p_max:.1f} hPa]).",
            )

    return True, None, None
