import math
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
MOLAR_MASS = {"no2": 46.0055, "so2": 64.066, "co": 28.0101, "o3": 47.9982, "nh3": 17.0305}
MOLAR_VOLUME_L = 8.314462618 * 298.15 / 101.325  # 25 C, 1 atmosphere


def number(value):
    try:
        result = float(str(value).strip())
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def to_utc(value, default_timezone=IST):
    if isinstance(value, datetime):
        parsed = value
    else:
        value = str(value).strip()
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            for fmt in (
                "%d-%m-%Y %H:%M",
                "%d-%m-%Y %H:%M:%S",
                "%d/%m/%Y %H:%M",
                "%d/%m/%Y %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
            ):
                try:
                    parsed = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"Unrecognized observation timestamp: {value}") from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=default_timezone)
    return parsed.astimezone(UTC)


def concentration(value, unit, pollutant):
    value = number(value)
    if value is None:
        return None
    normalized = str(unit).lower().replace("μ", "u").replace("µ", "u").replace("³", "3")
    normalized = normalized.replace(" ", "").replace("^", "")
    if normalized in {"ppb", "ppm"}:
        if pollutant not in MOLAR_MASS:
            raise ValueError(f"Gas mixing ratio cannot represent {pollutant}")
        micrograms = value * MOLAR_MASS[pollutant] / MOLAR_VOLUME_L
        if normalized == "ppm":
            micrograms *= 1000
    elif normalized in {"ug/m3", "ug/m³", "ugm-3"}:
        micrograms = value
    elif normalized in {"mg/m3", "mgm-3"}:
        micrograms = value * 1000
    else:
        raise ValueError(f"Unsupported concentration unit: {unit}")
    # Phase 1's canonical CO unit is mg/m3; other pollutants are ug/m3.
    return micrograms / 1000 if pollutant == "co" else micrograms


def wind_from_components(u, v):
    u, v = number(u), number(v)
    if u is None or v is None:
        return None, None
    speed = math.hypot(u, v)
    direction = (270 - math.degrees(math.atan2(v, u))) % 360 if speed else None
    return speed, direction


def humidity_from_dewpoint(temperature, dewpoint):
    temperature, dewpoint = number(temperature), number(dewpoint)
    if temperature is None or dewpoint is None:
        return None
    if temperature <= -243.04 or dewpoint <= -243.04:
        return None
    humidity = 100 * math.exp(
        17.625 * dewpoint / (243.04 + dewpoint) - 17.625 * temperature / (243.04 + temperature)
    )
    return min(100, max(0, humidity))
