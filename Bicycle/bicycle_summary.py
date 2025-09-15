import re
import sys
from typing import Tuple, Optional


def power_to_distance(
    power_w: float,
    duration_min: float,
    mass_kg: float = 80.0,
    wind_speed: float = 1.0,
    crr: float = 0.005,
    cda: float = 0.40,
    rho: float = 1.225,
    drivetrain_eff: float = 0.95,
) -> Tuple[float, float]:
    """Convert average cycling power into equivalent flat-road distance.

    Args:
        power_w (float): Average power in watts.
        duration_min (float): Duration in minutes.
        mass_kg (float, optional): Total mass of rider and bike in kg. Defaults to 80.0.
        wind_speed (float, optional): Headwind (+) or tailwind (-) in m/s. Defaults to 1.0.
        crr (float, optional): Rolling resistance coefficient. Defaults to 0.005.
        cda (float, optional): Aerodynamic drag area (m^2). Defaults to 0.40.
        rho (float, optional): Air density (kg/m^3). Defaults to 1.225.
        drivetrain_eff (float, optional): Drivetrain efficiency (0-1). Defaults to 0.95.

    Returns:
        Tuple[float, float]: Average speed in km/h and total distance in km.
    """
    # Effective power available to overcome resistances
    effective_power = power_w * drivetrain_eff

    # Rolling resistance force (constant w.r.t speed)
    f_roll = crr * mass_kg * 9.80665

    # Solve cubic: P = f_roll*v + 0.5*rho*cda*(v+wind)^3
    # We'll solve numerically (bisection)
    def power_at_speed(v: float) -> float:
        return f_roll * v + 0.5 * rho * cda * (v + wind_speed) ** 3

    # Bisection search between 0 and 20 m/s (~72 km/h)
    v_low, v_high = 0.0, 20.0
    for _ in range(100):
        v_mid = 0.5 * (v_low + v_high)
        if power_at_speed(v_mid) > effective_power:
            v_high = v_mid
        else:
            v_low = v_mid
    v = 0.5 * (v_low + v_high)

    speed_kmh = v * 3.6
    distance_km = speed_kmh * (duration_min / 60.0)
    return speed_kmh, distance_km


def distance_to_power(
    distance_km: float,
    duration_min: float,
    mass_kg: float = 80.0,
    wind_speed: float = 1.0,
    crr: float = 0.005,
    cda: float = 0.40,
    rho: float = 1.225,
    drivetrain_eff: float = 0.95,
) -> float:
    """Estimate required average power given distance and duration.

    Args:
        distance_km (float): Distance in km.
        duration_min (float): Duration in minutes.
        mass_kg (float, optional): Total mass of rider and bike in kg. Defaults to 80.0.
        wind_speed (float, optional): Headwind (+) or tailwind (-) in m/s. Defaults to 1.0.
        crr (float, optional): Rolling resistance coefficient. Defaults to 0.005.
        cda (float, optional): Aerodynamic drag area (m^2). Defaults to 0.40.
        rho (float, optional): Air density (kg/m^3). Defaults to 1.225.
        drivetrain_eff (float, optional): Drivetrain efficiency (0-1). Defaults to 0.95.

    Returns:
        float: Required average power in watts.
    """
    v = (distance_km / (duration_min / 60.0)) / 3.6  # convert km/h to m/s
    f_roll = crr * mass_kg * 9.80665
    effective_power = f_roll * v + 0.5 * rho * cda * (v + wind_speed) ** 3
    # Adjust for drivetrain efficiency
    required_power = effective_power / drivetrain_eff
    return required_power


def power_to_calories(power_w: float, duration_min: float, gross_efficiency: float = 0.25) -> float:
    """Estimate calories burned given average power and duration.

    Args:
        power_w (float): Average power in watts.
        duration_min (float): Duration in minutes.
        gross_efficiency (float, optional): Fraction of metabolic power converted to
            mechanical power. Defaults to 0.25.

    Returns:
        float: Calories burned (kcal).
    """
    # Energy in Joules (mechanical)
    mechanical_energy_j = power_w * duration_min * 60.0
    # Convert to metabolic energy
    metabolic_energy_j = mechanical_energy_j / gross_efficiency
    # Convert Joules to kilocalories (1 kcal = 4184 J)
    kcal = metabolic_energy_j / 4184.0
    return kcal


def process_line(
    line: str, weight_kg: float = 80.0, wind_speed: float = 1.0
) -> Optional[Tuple[float, float, float, float]]:
    """Process a single input line into duration, power, distance, and calories.

    Args:
        line (str): Input line containing duration and either power or distance.
        weight_kg (float, optional): Weight of the rider in kg. Defaults to 80.0.
        wind_speed (float, optional): Wind speed in m/s. Defaults to 1.

    Returns:
        Optional[Tuple[float, float, float, float]]: (duration_min, power_w, distance_km, calories),
        or None if parsing fails.
    """
    match = re.match(r".*- (\d+)min @ ([\d,.]+) (Watt|km)", line.strip())
    if not match:
        return None

    duration_min = float(match.group(1))
    value = float(match.group(2).replace(",", "."))
    unit = match.group(3)

    if unit.lower().startswith("watt"):
        power_w = value
        _, distance_km = power_to_distance(power_w, duration_min, mass_kg=weight_kg, wind_speed=wind_speed)
        calories = power_to_calories(power_w, duration_min)
    else:
        distance_km = value
        power_w = distance_to_power(distance_km, duration_min, mass_kg=weight_kg, wind_speed=wind_speed)
        calories = power_to_calories(power_w, duration_min)

    return duration_min, power_w, distance_km, calories


def process_all_entries(
    text: str, weight_kg: float = 80.0, wind_speed: float = 1.0
) -> Optional[Tuple[float, float, float, float, int]]:
    """Process multiple input lines and print totals.

    Args:
        text (str): Multiline string with one entry per line.

    Returns:
        total_minutes (float): Total duration in minutes.
        total_distance (float): Total distance in km.
        total_calories (float): Total calories burned in kcal.
        average_power (float): Average power in watts.
        count (int): Total count - how many entries
    """
    total_minutes = 0.0
    total_distance = 0.0
    total_calories = 0.0
    average_power = 0.0
    count = 0

    for line in text.strip().splitlines():
        result = process_line(line, weight_kg=weight_kg, wind_speed=wind_speed)
        if not result:
            continue
        duration_min, power_w, distance_km, calories = result
        total_minutes += duration_min
        total_distance += distance_km
        total_calories += calories
        average_power += power_w
        count += 1

    if count > 0:
        average_power /= count

    return total_minutes, total_distance, total_calories, average_power, count


if __name__ == "__main__":

    input_text = sys.argv[1] if len(sys.argv) >= 2 else ""
    if not input_text:
        print("No entries passed")
    else:
        # process all lines and print totals
        result = process_all_entries(input_text, weight_kg=80.0, wind_speed=1.0)
        if result:
            total_minutes, total_distance, total_calories, average_power, count = result
            print(
                f"Total statistics:\n  "
                f"- number of rides: {count},\n  "
                f"- duration: {total_minutes} min,\n  "
                f"- distance: {total_distance:.1f} km,\n  "
                f"- average power: {average_power:.1f} Watt,\n  "
                f"- calories: {total_calories:.0f} kcal\n"
            )
        # get the last line and print the results
        last_line = input_text.strip().splitlines()[-1]
        result = process_line(last_line, weight_kg=80.0, wind_speed=1.0)
        if result:
            duration, power, distance, calories = result
            equivalent_append_distance, equivalent_append_wattage = "", ""
            if "Watt" in last_line:
                equivalent_append_distance = "(equivalent)"
            else:
                equivalent_append_wattage = "(equivalent)"
            print(
                f"Last entry statistics:\n  - duration: {duration} min,\n  "
                f"- distance {equivalent_append_distance}: {distance:.1f} km,\n  "
                f"- power {equivalent_append_wattage}: {power:.1f} Watt,\n  "
                f"- calories: {calories:.0f} kcal"
            )
