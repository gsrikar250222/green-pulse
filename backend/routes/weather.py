"""
GreenPulse – Weather & Agro-Advisory routes
  GET /weather        – live weather + 7-day forecast + agricultural advisories
  GET /weather/search – village, mandal & district search (local AP/Telangana db + Open-Meteo)
"""
from fastapi import APIRouter, Query, HTTPException
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any
import math

router = APIRouter(prefix="/weather", tags=["Weather"])

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
GEOCODE    = "https://geocoding-api.open-meteo.com/v1/search"

WMO_CODES = {
    0:  "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}

WMO_TELUGU = {
    0:  "స్పష్టమైన ఆకాశం (Clear)",
    1:  "దాదాపు స్పష్టమైన వాతావరణం",
    2:  "కొంత మేఘావృతం",
    3:  "పూర్తిగా మేఘావృతం",
    45: "పొగమంచు",
    51: "చిరుజల్లులు",
    53: "మోస్తరు చిరుజల్లులు",
    55: "దట్టమైన జల్లులు",
    61: "తేలికపాటి వర్షం",
    63: "మోస్తరు వర్షం",
    65: "భారీ వర్షం",
    80: "వర్షపు జల్లులు",
    81: "మోస్తరు జల్లులు",
    82: "తీవ్రమైన జల్లులు",
    95: "ఉరుములతో కూడిన వర్షం",
}

WMO_ICONS = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "❄️", 75: "❄️",
    80: "🌦️", 81: "🌧️", 82: "⛈️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}

# Curated agricultural villages, mandals, and districts across Andhra Pradesh & Telangana
LOCAL_AGRI_CENTERS = [
    {"name": "Guntur", "state": "Andhra Pradesh", "country": "India", "district": "Guntur", "lat": 16.3067, "lon": 80.4365, "type": "District Hub"},
    {"name": "Tenali", "state": "Andhra Pradesh", "country": "India", "district": "Guntur", "lat": 16.2430, "lon": 80.6400, "type": "Mandal / Village"},
    {"name": "Mangalagiri", "state": "Andhra Pradesh", "country": "India", "district": "Guntur", "lat": 16.4319, "lon": 80.5543, "type": "Mandal"},
    {"name": "Amaravati", "state": "Andhra Pradesh", "country": "India", "district": "Guntur", "lat": 16.5131, "lon": 80.5165, "type": "Capital Region"},
    {"name": "Bapatla", "state": "Andhra Pradesh", "country": "India", "district": "Bapatla", "lat": 15.9042, "lon": 80.4673, "type": "Agri College Hub"},
    {"name": "Narasaraopet", "state": "Andhra Pradesh", "country": "India", "district": "Palnadu", "lat": 16.2359, "lon": 80.0499, "type": "Mandal"},
    {"name": "Sattenapalle", "state": "Andhra Pradesh", "country": "India", "district": "Palnadu", "lat": 16.3986, "lon": 80.1804, "type": "Mandal"},
    {"name": "Chilakaluripet", "state": "Andhra Pradesh", "country": "India", "district": "Palnadu", "lat": 16.0892, "lon": 80.1672, "type": "Mandal"},
    {"name": "Vijayawada", "state": "Andhra Pradesh", "country": "India", "district": "NTR", "lat": 16.5062, "lon": 80.6480, "type": "District Hub"},
    {"name": "Gudivada", "state": "Andhra Pradesh", "country": "India", "district": "Krishna", "lat": 16.4410, "lon": 80.9926, "type": "Paddy Region"},
    {"name": "Machilipatnam", "state": "Andhra Pradesh", "country": "India", "district": "Krishna", "lat": 16.1875, "lon": 81.1389, "type": "Coastal Mandal"},
    {"name": "Ongole", "state": "Andhra Pradesh", "country": "India", "district": "Prakasam", "lat": 15.5057, "lon": 80.0499, "type": "District Hub"},
    {"name": "Chirala", "state": "Andhra Pradesh", "country": "India", "district": "Bapatla", "lat": 15.8246, "lon": 80.3522, "type": "Coastal Mandal"},
    {"name": "Rajahmundry", "state": "Andhra Pradesh", "country": "India", "district": "East Godavari", "lat": 17.0005, "lon": 81.8040, "type": "Godavari Belt"},
    {"name": "Kakinada", "state": "Andhra Pradesh", "country": "India", "district": "Kakinada", "lat": 16.9891, "lon": 82.2475, "type": "District Hub"},
    {"name": "Eluru", "state": "Andhra Pradesh", "country": "India", "district": "Eluru", "lat": 16.7107, "lon": 81.0952, "type": "Paddy / Aqua Belt"},
    {"name": "Bhimavaram", "state": "Andhra Pradesh", "country": "India", "district": "West Godavari", "lat": 16.5449, "lon": 81.5212, "type": "Paddy / Aqua Belt"},
    {"name": "Kurnool", "state": "Andhra Pradesh", "country": "India", "district": "Kurnool", "lat": 15.8281, "lon": 78.0373, "type": "Rayalaseema Hub"},
    {"name": "Nandyal", "state": "Andhra Pradesh", "country": "India", "district": "Nandyal", "lat": 15.4886, "lon": 78.4836, "type": "Seed Capital"},
    {"name": "Anantapur", "state": "Andhra Pradesh", "country": "India", "district": "Anantapur", "lat": 14.6819, "lon": 77.6006, "type": "Groundnut Hub"},
    {"name": "Kadapa", "state": "Andhra Pradesh", "country": "India", "district": "YSR Kadapa", "lat": 14.4673, "lon": 78.8242, "type": "Rayalaseema Hub"},
    {"name": "Nellore", "state": "Andhra Pradesh", "country": "India", "district": "SPSR Nellore", "lat": 14.4426, "lon": 79.9865, "type": "Rice Bowl"},
    {"name": "Tirupati", "state": "Andhra Pradesh", "country": "India", "district": "Tirupati", "lat": 13.6288, "lon": 79.4192, "type": "District Hub"},
    {"name": "Visakhapatnam", "state": "Andhra Pradesh", "country": "India", "district": "Visakhapatnam", "lat": 17.6868, "lon": 83.2185, "type": "North Coastal Hub"},
    {"name": "Warangal", "state": "Telangana", "country": "India", "district": "Warangal", "lat": 17.9689, "lon": 79.5941, "type": "Cotton / Chilli Hub"},
    {"name": "Khammam", "state": "Telangana", "country": "India", "district": "Khammam", "lat": 17.2473, "lon": 80.1514, "type": "Chilli Belt"},
    {"name": "Karimnagar", "state": "Telangana", "country": "India", "district": "Karimnagar", "lat": 18.4386, "lon": 79.1288, "type": "Paddy Region"},
    {"name": "Nizamabad", "state": "Telangana", "country": "India", "district": "Nizamabad", "lat": 18.6725, "lon": 78.0941, "type": "Turmeric Hub"},
    {"name": "Nalgonda", "state": "Telangana", "country": "India", "district": "Nalgonda", "lat": 17.0575, "lon": 79.2684, "type": "Cotton / Sweet Lime"},
    {"name": "Hyderabad", "state": "Telangana", "country": "India", "district": "Hyderabad", "lat": 17.3850, "lon": 78.4867, "type": "Capital Hub"},
]


def generate_agricultural_advisory(temp: float, humidity: float, wind_speed: float, rain_prob: int) -> Dict[str, Any]:
    """Generate dynamic farming advisories based on meteorological metrics."""
    # Spraying Suitability
    if wind_speed > 18:
        spraying = {
            "status": "Not Recommended",
            "en": "High wind speeds (>18 km/h). Postpone pesticide or foliar fertilizer spraying to avoid drift loss.",
            "te": "ఎక్కువ గాలులు వీస్తున్నాయి (>18 km/h). మందుల పిచికారీ వాయిదా వేయండి.",
            "color": "danger"
        }
    elif rain_prob > 55:
        spraying = {
            "status": "Postpone",
            "en": "Rain probability is high (>55%). Do not spray now as chemical wash-off will occur.",
            "te": "వర్ష సూచన ఉంది (>55%). రసాయనాలు కొట్టుకుపోయే ప్రమాదం ఉన్నందున పిచికారీ చేయవద్దు.",
            "color": "warning"
        }
    else:
        spraying = {
            "status": "Suitable",
            "en": "Weather conditions are optimal for foliar and pesticide spraying (early morning or late evening).",
            "te": "మందుల పిచికారీకి వాతావరణం అనుకూలంగా ఉంది (ఉదయం లేదా సాయంత్రం వేళల్లో చేయండి).",
            "color": "success"
        }

    # Irrigation Advice
    if rain_prob > 60:
        irrigation = {
            "status": "Delay Irrigation",
            "en": "Significant rainfall expected. Hold off irrigation to conserve power and prevent waterlogging.",
            "te": "వర్షం పడే అవకాశం ఉంది. నీటిపారుదల నిలిపివేసి నీరు నిల్వ ఉండకుండా చూడండి.",
            "color": "warning"
        }
    elif temp > 36 and humidity < 40:
        irrigation = {
            "status": "Irrigation Needed",
            "en": "High heat and low humidity. Provide light irrigation to prevent moisture stress in crops.",
            "te": "తీవ్రమైన ఎండ మరియు తేమ తక్కువగా ఉంది. పంటలకు తేలికపాటి తడులు ఇవ్వండి.",
            "color": "danger"
        }
    else:
        irrigation = {
            "status": "Normal Irrigation",
            "en": "Standard crop-specific irrigation schedule may be followed.",
            "te": "సాధారణ పద్ధతిలో నీటి తడులు అందించవచ్చు.",
            "color": "success"
        }

    # Harvest & Sowing Advice
    if rain_prob > 70:
        harvest = {
            "status": "Protect Harvest",
            "en": "Keep harvested grain, cotton, and chilli produce covered in safe storage.",
            "te": "కోసిన పంటలు, పత్తి, మిరప తడిసిపోకుండా సురక్షిత ప్రాంతాల్లో భద్రపరచండి.",
            "color": "danger"
        }
    else:
        harvest = {
            "status": "Favorable",
            "en": "Favorable dry conditions for harvesting, threshing, and sun-drying agricultural produce.",
            "te": "పంట కోతలు, నూర్పిళ్లు మరియు ఎండబెట్టడానికి అనుకూలమైన వాతావరణం.",
            "color": "success"
        }

    return {
        "spraying":   spraying,
        "irrigation": irrigation,
        "harvest":    harvest,
    }


def generate_fallback_weather(lat: float, lon: float, city: str) -> Dict[str, Any]:
    """Generates realistic seasonal agricultural weather when external API is unreachable."""
    base_temp = 31.0 + (lat % 2)
    current_time = datetime.now()
    days_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    forecast = []
    for i in range(7):
        target_date = current_time + timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")
        day_wmo = 1 if i % 3 != 0 else 2
        forecast.append({
            "date":       date_str,
            "day":        days_names[target_date.weekday()],
            "weather":    WMO_CODES.get(day_wmo, "Mainly clear"),
            "weather_te": WMO_TELUGU.get(day_wmo, "స్పష్టమైన వాతావరణం"),
            "icon":       WMO_ICONS.get(day_wmo, "🌤️"),
            "temp_max":   round(base_temp + (i % 3) - 1, 1),
            "temp_min":   round(base_temp - 8.5 + (i % 2), 1),
            "rain_prob":  (i * 12) % 45,
            "wind_max":   round(11.0 + (i % 4), 1),
        })

    advisory = generate_agricultural_advisory(
        temp=round(base_temp, 1),
        humidity=62.0,
        wind_speed=12.5,
        rain_prob=15,
    )

    return {
        "city": city,
        "state": "Andhra Pradesh",
        "lat": lat,
        "lon": lon,
        "current": {
            "temperature":   round(base_temp, 1),
            "humidity":      62.0,
            "wind_speed":    12.5,
            "precipitation": 0.0,
            "weather":       "Mainly clear",
            "weather_te":    "స్పష్టమైన వాతావరణం",
            "icon":          "🌤️",
        },
        "forecast": forecast,
        "advisory": advisory,
        "is_live": False,
    }


@router.get("")
async def get_weather(
    lat:  float = Query(16.3067, description="Latitude"),
    lon:  float = Query(80.4365, description="Longitude"),
    city: str   = Query("Guntur", description="City/Village name for display"),
):
    params = {
        "latitude":        lat,
        "longitude":       lon,
        "current":         "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,precipitation",
        "daily":           "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
        "timezone":        "Asia/Kolkata",
        "forecast_days":   7,
    }

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            res = await client.get(OPEN_METEO, params=params)
            if res.status_code != 200:
                return generate_fallback_weather(lat, lon, city)
            data = res.json()
    except Exception:
        # Graceful fallback so frontend weather never fails
        return generate_fallback_weather(lat, lon, city)

    current = data.get("current", {})
    daily   = data.get("daily", {})

    wmo_code = current.get("weather_code", 0)
    temp     = current.get("temperature_2m", 30.0)
    humidity = current.get("relative_humidity_2m", 60.0)
    wind     = current.get("wind_speed_10m", 12.0)
    rain     = current.get("precipitation", 0.0)

    forecast = []
    days     = daily.get("time", [])
    days_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    for i, day in enumerate(days):
        code = daily.get("weather_code", [])[i] if i < len(daily.get("weather_code", [])) else 0
        date_obj = datetime.strptime(day, "%Y-%m-%d") if isinstance(day, str) else datetime.now()
        forecast.append({
            "date":       day,
            "day":        days_names[date_obj.weekday()],
            "weather":    WMO_CODES.get(code, "Clear"),
            "weather_te": WMO_TELUGU.get(code, "స్పష్టమైన వాతావరణం"),
            "icon":       WMO_ICONS.get(code, "🌡️"),
            "temp_max":   daily.get("temperature_2m_max", [])[i] if i < len(daily.get("temperature_2m_max",[])) else "--",
            "temp_min":   daily.get("temperature_2m_min", [])[i] if i < len(daily.get("temperature_2m_min",[])) else "--",
            "rain_prob":  daily.get("precipitation_probability_max", [])[i] if i < len(daily.get("precipitation_probability_max",[])) else 0,
            "wind_max":   daily.get("wind_speed_10m_max", [])[i] if i < len(daily.get("wind_speed_10m_max",[])) else "--",
        })

    first_rain_prob = forecast[0]["rain_prob"] if forecast else 0
    advisory = generate_agricultural_advisory(
        temp=float(temp) if isinstance(temp, (int, float)) else 30.0,
        humidity=float(humidity) if isinstance(humidity, (int, float)) else 60.0,
        wind_speed=float(wind) if isinstance(wind, (int, float)) else 10.0,
        rain_prob=int(first_rain_prob) if isinstance(first_rain_prob, (int, float)) else 0,
    )

    return {
        "city":     city,
        "lat":      lat,
        "lon":      lon,
        "current": {
            "temperature":   temp,
            "humidity":      humidity,
            "wind_speed":    wind,
            "precipitation": rain,
            "weather":       WMO_CODES.get(wmo_code, "Clear"),
            "weather_te":    WMO_TELUGU.get(wmo_code, "స్పష్టమైన వాతావరణం"),
            "icon":          WMO_ICONS.get(wmo_code, "☀️"),
        },
        "forecast": forecast,
        "advisory": advisory,
        "is_live":  True,
    }


@router.get("/search")
async def search_city(q: str = Query(..., min_length=2)):
    """Search village, mandal, or city name for weather lookup (AP/Telangana + global)."""
    q_clean = q.strip().lower()
    results = []

    # 1. Local agricultural database search (priority for Andhra & Telangana farmers)
    for c in LOCAL_AGRI_CENTERS:
        if q_clean in c["name"].lower() or q_clean in c.get("district", "").lower() or q_clean in c.get("type", "").lower():
            results.append({
                "name":     c["name"],
                "state":    c["state"],
                "district": c.get("district", ""),
                "country":  c["country"],
                "lat":      c["lat"],
                "lon":      c["lon"],
                "type":     c.get("type", "Agricultural Region"),
            })

    # 2. Open-Meteo geocoding search for broader national coverage
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.get(GEOCODE, params={"name": q.strip(), "count": 6, "language": "en", "format": "json"})
            if res.status_code == 200:
                data = res.json()
                for r in data.get("results", []):
                    name = r.get("name")
                    # Deduplicate with local database
                    if not any(res_item["name"].lower() == name.lower() for res_item in results):
                        results.append({
                            "name":     name,
                            "state":    r.get("admin1", ""),
                            "district": r.get("admin2", ""),
                            "country":  r.get("country", ""),
                            "lat":      r.get("latitude"),
                            "lon":      r.get("longitude"),
                            "type":     "Location",
                        })
    except Exception:
        pass

    return results[:8]
