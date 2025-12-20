import re
import sys
from typing import Tuple, Optional
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt


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
) -> Optional[Tuple[float, float, float, float, int, dict]]:
    """Process multiple input lines and return totals.

    Args:
        text (str): Multiline string with one entry per line.
        weight_kg (float): Weight of the rider in kg. Defaults to 80.0.
        wind_speed (float): Wind speed in m/s. Defaults to 1.0.

    Returns:
        Optional[Tuple[float, float, float, float, int, dict]]: (total_minutes, total_distance, total_calories,
            average_power, count, monthly_data)
    """
    total_minutes = 0.0
    total_distance = 0.0
    total_calories = 0.0
    total_power = 0.0
    count = 0
    monthly_data = {}  # Store data by (year, month)

    for line in text.strip().splitlines():
        result = process_line(line, weight_kg=weight_kg, wind_speed=wind_speed)
        if not result:
            continue
        duration_min, power_w, distance_km, calories = result
        total_minutes += duration_min
        total_distance += distance_km
        total_calories += calories
        total_power += power_w
        count += 1

        # Extract date from line
        match = re.match(r"\s*-\s*(\d{2}\.\d{2}\.\d{4})\s*-\s*(\d+)min\s*@\s*([\d,.]+)\s*(Watt|km)", line.strip())
        if match:
            date_str = match.group(1)
            try:
                date = datetime.strptime(date_str, "%d.%m.%Y")
                year_month = (date.year, date.month)
                if year_month not in monthly_data:
                    monthly_data[year_month] = {"distance": 0.0, "power": 0.0, "count": 0}
                monthly_data[year_month]["distance"] += distance_km
                monthly_data[year_month]["power"] += power_w
                monthly_data[year_month]["count"] += 1
            except ValueError:
                continue

    average_power = total_power / count if count > 0 else 0.0
    return total_minutes, total_distance, total_calories, average_power, count, monthly_data


def format_with_trend_arrow(
    value: float,
    average: float,
    tolerance: float = 0.0,
    unit: str = "",
) -> str:
    """
    Returns a formatted string of the value with a trend arrow indicating how it compares to the average.

    The arrow is:
    - ↑ if value > average + tolerance
    - ↓ if value < average - tolerance
    - → if within tolerance of the average

    Parameters
    ----------
    value : float
        The current value to display (e.g., last ride's distance, power, or calories).
    average : float
        The overall average across all records for comparison.
    tolerance : float, default 0.0
        Threshold for considering the value "equal" to the average.
        Recommended values:
        - 0.1 for distance_km
        - 2 for power_w
        - 10 for calories
        - 1 for duration_min
    unit : str, default ""
        Unit string to append (e.g., "km", "Watt", "kcal", "min").
        Also used to determine default formatting precision.

    Returns
    -------
    str
        Formatted string in the form "XX.X unit arrow" (e.g., "21.3 km ↑").

    Examples
    --------
    >>> format_with_trend_arrow(25.5, 21.1, tolerance=0.1, unit="km")
    '25.5 km ↑'
    >>> format_with_trend_arrow(160, 157, tolerance=2, unit="Watt")
    '160 Watt →'
    """
    diff = value - average

    if diff > tolerance:
        arrow = " ↑"
    elif diff < -tolerance:
        arrow = " ↓"
    else:
        arrow = " →"

    # Determine formatting based on unit (common cycling metrics)
    if unit.lower() in ["km", "distance"]:
        formatted_value = f"{value:.1f}"
    elif unit.lower() in ["watt", "w", "power"]:
        formatted_value = f"{value:.0f}"
    elif unit.lower() in ["kcal", "calories"]:
        formatted_value = f"{value:.0f}"
    elif unit.lower() in ["min", "minutes"]:
        formatted_value = f"{value:.0f}"
    else:
        # Fallback: 1 decimal place
        formatted_value = f"{value:.1f}"

    # Strip any leading/trailing space from unit if empty
    unit_part = f" {unit}" if unit else ""
    return f"{formatted_value}{unit_part}{arrow}"


def print_last_entry_stats(df: pd.DataFrame) -> None:
    """
    Prints the last entry statistics with trend arrows compared to overall averages.
    """
    if df.empty:
        return

    # Precompute averages
    avg_distance = df["distance_km"].mean()
    avg_power = df["power_w"].mean()
    avg_calories = df["calories"].mean()

    # Last ride
    last = df.iloc[-1]

    print(
        "Last entry statistics:\n"
        f"  - duration: {format_with_trend_arrow(last['duration_min'], df['duration_min'].mean(), tolerance=1, unit='min')}\n"
        f"  - distance: {format_with_trend_arrow(last['distance_km'], avg_distance, tolerance=0.1, unit='km')}\n"
        f"  - calories: {format_with_trend_arrow(last['calories'], avg_calories, tolerance=10, unit='kcal')}\n"
        f"  - power: {format_with_trend_arrow(last['power_w'], avg_power, tolerance=2, unit='Watt')}\n"
    )


def entries_to_dataframe(text: str, weight_kg: float = 80.0, wind_speed: float = 1.0) -> pd.DataFrame:
    """
    Parse cycling entries using pandas for easier analysis.

    Args:
        text (str): Multiline string with one entry per line.
        weight_kg (float): Weight of the rider in kg.
        wind_speed (float): Wind speed in m/s.

    Returns:
        pd.DataFrame: DataFrame with columns: date, duration_min, power_w, distance_km, calories, unit
    """
    rows = []
    for line in text.strip().splitlines():
        match = re.match(r"\s*-\s*(\d{2}\.\d{2}\.\d{4})\s*-\s*(\d+)min\s*@\s*([\d,.]+)\s*(Watt|km)", line.strip())
        if not match:
            continue
        date_str = match.group(1)
        duration_min = float(match.group(2))
        value = float(match.group(3).replace(",", "."))
        unit = match.group(4)
        try:
            date = datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            continue

        if unit.lower().startswith("watt"):
            power_w = value
            _, distance_km = power_to_distance(power_w, duration_min, mass_kg=weight_kg, wind_speed=wind_speed)
            calories = power_to_calories(power_w, duration_min)
        else:
            distance_km = value
            power_w = distance_to_power(distance_km, duration_min, mass_kg=weight_kg, wind_speed=wind_speed)
            calories = power_to_calories(power_w, duration_min)

        rows.append(
            {
                "date": date,
                "duration_min": duration_min,
                "power_w": power_w,
                "distance_km": distance_km,
                "calories": calories,
                "unit": unit,
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.join(df.distance_km.cumsum().to_frame().rename(columns={"distance_km": "distance_cumsum_km"}))
        df = df.join(df.calories.cumsum().to_frame().rename(columns={"calories": "calories_cumsum"}))
        df = df.assign(doy=df["date"].dt.dayofyear)
    return df


def generate_ascii_bar(value: float, max_value: float, max_length: int = 10) -> str:
    """Generate an ASCII bar representation for a value.

    Args:
        value (float): The value to represent.
        max_value (float): The maximum value for scaling the bar.
        max_length (int): Maximum length of the bar in characters.

    Returns:
        str: ASCII bar representation.
    """
    if max_value == 0:
        return "[]"
    bar_length = int((value / max_value) * max_length)
    bar_length = max(0, min(bar_length, max_length))
    return "|" + "█" * bar_length + " " * (max_length - bar_length)


if __name__ == "__main__":
    input_arg = sys.argv[1] if len(sys.argv) >= 2 else ""
    plot_arg = sys.argv[2] if len(sys.argv) >= 3 else ""
    input_text = ""

    if not input_arg:
        print("No entries passed")
        sys.exit(1)
    if input_arg.endswith(".txt"):
        try:
            with open(input_arg, "r", encoding="utf-8") as f:
                input_text = f.read()
        except Exception as e:
            print(f"Failed to read file: {e}")
            sys.exit(1)
    else:
        input_text = input_arg

    # Process all lines and get totals and monthly data. Use weight that includes bike!
    df = entries_to_dataframe(input_text, weight_kg=80.0, wind_speed=1.0)
    if not df.empty:

        if plot_arg.lower() == "plot":
            # give more space for easier reading when shon in PyTO console
            print("\n")

        # Get the last line and print the results
        unit = df.iloc[-1]["unit"]
        equivalent_append_distance, equivalent_append_wattage = "", ""
        if "Watt" in unit:
            equivalent_append_distance = ""
        else:
            equivalent_append_wattage = ""
        print_last_entry_stats(df)

        print(
            f"Average statistics:\n  "
            f"- duration: {df.duration_min.mean():.0f} min\n  "
            f"- distance/ride: {df.distance_km.mean():.1f} km\n  "
            f"- distance/day: {df.distance_km.sum() / (df.date.max() - df.date.min()).days:.1f} km\n  "
            f"- calories: {df.calories.mean():.0f} kcal\n  "
            f"- power: {df.power_w.mean():.0f} Watt\n\n"
            f"Total statistics:\n  "
            f"- duration: {df.duration_min.sum():.0f} min\n  "
            f"- distance: {df.distance_km.sum():.1f} km\n  "
            f"- calories: {df.calories.sum():.0f} kcal\n  "
            f"- number of rides: {df.shape[0]}\n  "
        )

        # Monthly comparison
        df_monthly = df.groupby(df["date"].dt.to_period("M")).agg(
            distance_mean_km=("distance_km", "mean"),
            distance_sum_km=("distance_km", "sum"),
            power_mean_w=("power_w", "mean"),
            count=("date", "count"),
        )
        # ensure existance of last 3 months
        all_periods = pd.period_range(df["date"].iloc[-1] - pd.DateOffset(months=12), df["date"].iloc[-1], freq="M")
        df_monthly = df_monthly.reindex(all_periods, fill_value=0)

        # Find maximum values for scaling bars
        max_distance = df_monthly.tail(3)["distance_mean_km"].max()
        max_power = df_monthly.tail(3)["power_mean_w"].max()

        # Generate ASCII bars
        three_distance_bar = generate_ascii_bar(df_monthly.tail(3).distance_mean_km.iloc[0], max_distance)
        two_distance_bar = generate_ascii_bar(df_monthly.tail(3).distance_mean_km.iloc[1], max_distance)
        current_distance_bar = generate_ascii_bar(df_monthly.tail(3).distance_mean_km.iloc[2], max_distance)
        three_power_bar = generate_ascii_bar(df_monthly.tail(3).power_mean_w.iloc[0], max_power if max_power > 0 else 1)
        two_power_bar = generate_ascii_bar(df_monthly.tail(3).power_mean_w.iloc[1], max_power if max_power > 0 else 1)
        current_power_bar = generate_ascii_bar(
            df_monthly.tail(3).power_mean_w.iloc[2], max_power if max_power > 0 else 1
        )
        max_count = df_monthly.tail(3)["count"].max() if df_monthly.tail(3)["count"].max() > 0 else 1
        three_count_bar = generate_ascii_bar(df_monthly.tail(3)["count"].iloc[0], max_count)
        two_count_bar = generate_ascii_bar(df_monthly.tail(3)["count"].iloc[1], max_count)
        current_count_bar = generate_ascii_bar(df_monthly.tail(3)["count"].iloc[2], max_count)
        print(
            f"Last 3 months - Mean Distance:\n"
            f"{three_distance_bar} {df_monthly.tail(3).distance_mean_km.iloc[0]:.1f}km\n"
            f"{two_distance_bar} {df_monthly.tail(3).distance_mean_km.iloc[1]:.1f}km\n"
            f"{current_distance_bar} {df_monthly.tail(3).distance_mean_km.iloc[2]:.1f}km\n\n"
            f"Average Power:\n"
            f"{three_power_bar} {df_monthly.tail(3).power_mean_w.iloc[0]:.1f}W\n"
            f"{two_power_bar} {df_monthly.tail(3).power_mean_w.iloc[1]:.1f}W\n"
            f"{current_power_bar} {df_monthly.tail(3).power_mean_w.iloc[2]:.1f}W\n\n"
            f"Number of rides:\n"
            f"{three_count_bar} {df_monthly.tail(3)['count'].iloc[0]:.0f}\n"
            f"{two_count_bar} {df_monthly.tail(3)['count'].iloc[1]:.0f}\n"
            f"{current_count_bar} {df_monthly.tail(3)['count'].iloc[2]:.0f}\n"
        )

        if plot_arg.lower() == "plot" and df.empty is False:
            df_monthly.index = df_monthly.index.to_timestamp()
            df_monthly = df_monthly.reset_index()
            df_monthly = df_monthly.rename(columns={"index": "date"})
            df_monthly.date = pd.to_datetime(df_monthly.date) + pd.offsets.DateOffset(days=15)
            df.date = pd.to_datetime(df.date)
            df_plot = pd.merge(
                df[["date", "distance_cumsum_km"]], df_monthly[["date", "distance_sum_km"]], on="date", how="outer"
            )

            fig, ax1 = plt.subplots(figsize=(10, 6))
            ax1.set_xlabel("Date")
            ax1.set_ylabel("Monthly Distance (km)", color="tab:blue")
            bars = ax1.bar(
                df_plot["date"],
                df_plot["distance_sum_km"],
                label="Monthly Distance",
                color="tab:blue",
                width=28,
            )
            ax1.tick_params(axis="y", labelcolor="tab:blue")
            ax2 = ax1.twinx()
            ax2.set_ylabel("Cumulative Distance (km)", color="tab:red")
            line = ax2.plot(
                df_plot["date"],
                df_plot["distance_cumsum_km"],
                label="Cumulative Distance",
                color="tab:red",
                linewidth=2,
            )
            ax2.tick_params(axis="y", labelcolor="tab:red")

            plt.tight_layout()
            plt.show()
