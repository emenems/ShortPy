import re
import sys
from typing import Tuple
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


def generate_ascii_bar(value: float, max_value: float, max_length: int = 13) -> str:
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


def format_with_trend_arrow(
    value: float,
    average: float,
    tolerance: float = 0.1,
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
    tolerance : float, default 0.1
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

    if unit.lower() in ["km", "distance"]:
        formatted_value = f"{value:.1f}"
    elif unit.lower() in ["watt", "w", "power"]:
        formatted_value = f"{value:.0f}"
    elif unit.lower() in ["kcal", "calories"]:
        formatted_value = f"{value:.0f}"
    elif unit.lower() in ["min", "minutes"]:
        formatted_value = f"{value:.0f}"
    else:
        formatted_value = f"{value:.1f}"

    # Strip any leading/trailing space from unit if empty
    unit_part = f" {unit}" if unit else ""
    return f"{formatted_value}{unit_part}{arrow}"


def print_stats(df: pd.DataFrame, add_totals: bool = False, add_average: bool = False) -> None:
    """
    Prints the last entry statistics with trend arrows compared to overall averages.
    """
    if df.empty:
        return

    # Last ride
    last = df.iloc[-1]
    year = last["date"].year

    # Overall averages - this and previous year
    df_year = df[df["date"].dt.year == year]
    df_prev_year = df[df["date"].dt.year == year - 1]

    if df_prev_year.empty:
        df_prev_year = pd.DataFrame(columns=df.columns, data=[[0] * len(df.columns)])

    print(
        "Last entry:\n"
        f"  - duration: {format_with_trend_arrow(last['duration_min'], df_year['duration_min'].mean(), tolerance=1, unit='min')}\n"
        f"  - distance: {format_with_trend_arrow(last['distance_km'], df_year['distance_km'].mean(), tolerance=0.1, unit='km')}\n"
        f"  - calories: {format_with_trend_arrow(last['calories'], df_year['calories'].mean(), tolerance=10, unit='kcal')}\n"
        f"  - power: {format_with_trend_arrow(last['power_w'], df_year['power_w'].mean(), tolerance=2, unit='Watt')}\n"
    )
    if add_average:
        print(
            f"Average statistics vs {year - 1}:\n  "
            f"- duration: {df_year.duration_min.mean():.0f} vs {df_prev_year.duration_min.mean():.0f} min\n  "
            f"- distance/ride: {df_year.distance_km.mean():.1f} vs {df_prev_year.distance_km.mean():.1f} km\n  "
            f"- calories: {df_year.calories.mean():.0f} vs {df_prev_year.calories.mean():.0f} kcal\n  "
            f"- power: {df_year.power_w.mean():.0f} vs {df_prev_year.power_w.mean():.0f} Watt\n"
        )
    if add_totals or df_prev_year.distance_km.sum() == 0:
        print(
            f"Totals in {year}:\n  "
            f"- duration: {df_year.duration_min.sum():.0f}\n  "
            f"- distance: {df_year.distance_km.sum():.1f}\n  "
            f"- calories: {df_year.calories.sum():.0f}\n  "
            f"- Rides: {df_year.shape[0]}\n"
        )


def print_charts(df_monthly: pd.DataFrame, last_x: int = 3) -> None:
    """
    Prints ASCII bar charts for the last X months of cycling statistics.
    """
    metrics = [
        ("distance_mean_km", "Mean Distance", "{:.1f}km"),
        ("power_mean_w", "Mean Power", "{:.0f}W"),
        ("count", "Rides", "{:.0f}"),
    ]
    last_x_months = df_monthly.tail(last_x)
    ascii_bars = {}
    for col, _, _ in metrics:
        max_val = last_x_months[col].max() if last_x_months[col].max() > 0 else 1
        ascii_bars[col] = [generate_ascii_bar(val, max_val) for val in last_x_months[col]]
    for _, (col, label, fmt) in enumerate(metrics):
        print(f"{label} (last {last_x} months):")
        for i in range(last_x):
            print(f"{ascii_bars[col][i]} {fmt.format(last_x_months[col].iloc[i])}")
        print("")


def plot_distance(df: pd.DataFrame, df_monthly: pd.DataFrame) -> None:
    """
    Plot cumulative distance over time.

    Args:
        df (pd.DataFrame): DataFrame with cycling entries.
    """
    df_monthly.index = df_monthly.index.to_timestamp()
    df_monthly = df_monthly.reset_index()
    df_monthly = df_monthly.rename(columns={"index": "date"})
    df_monthly.date = pd.to_datetime(df_monthly.date) + pd.offsets.DateOffset(days=15)
    df.date = pd.to_datetime(df.date)
    df_plot = pd.merge(
        df[["date", "distance_cumsum_km"]], df_monthly[["date", "distance_sum_km"]], on="date", how="outer"
    )

    _, ax1 = plt.subplots(figsize=(10, 6))
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Monthly Distance (km)", color="tab:blue")
    ax1.bar(
        df_plot["date"],
        df_plot["distance_sum_km"],
        label="Monthly Distance",
        color="tab:blue",
        width=28,
    )
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    ax2 = ax1.twinx()
    ax2.set_ylabel("Cumulative Distance (km)", color="tab:red")
    ax2.plot(
        df_plot["date"],
        df_plot["distance_cumsum_km"],
        label="Cumulative Distance",
        color="tab:red",
        linewidth=2,
    )
    ax2.tick_params(axis="y", labelcolor="tab:red")

    plt.tight_layout()
    plt.show()


def print_yearly_goals(df: pd.DataFrame) -> None:
    """Print progress towards matching previous year's totals."""
    if df.empty:
        return

    current_year = df["date"].dt.year.max()
    df_current = df[df["date"].dt.year == current_year]
    df_prev = df[df["date"].dt.year == current_year - 1]

    if df_prev.empty:
        return

    # Previous year totals = goals for current year
    goal_distance = df_prev["distance_km"].sum()
    goal_rides = len(df_prev)
    goal_calories = df_prev["calories"].sum()
    goal_duration = df_prev["duration_min"].sum()

    # Current progress
    curr_distance = df_current["distance_km"].sum()
    curr_rides = len(df_current)
    curr_calories = df_current["calories"].sum()
    curr_duration = df_current["duration_min"].sum()

    def progress_bar(current: float, goal: float, width: int = 13) -> str:
        if goal == 0:
            return "░" * width
        ratio = min(current / goal, 1.0)
        filled = int(ratio * width)
        return "█" * filled + "░" * (width - filled)

    def pct(current: float, goal: float) -> int:
        return int(100 * current / goal) if goal > 0 else 0

    print(f"Compared to {current_year - 1}:")
    print(
        f"Distance: {curr_distance:.1f} / {goal_distance:.1f} km\n|{progress_bar(curr_distance, goal_distance)} {pct(curr_distance, goal_distance):2}%"
    )
    print(
        f"Calories: {curr_calories:.0f} / {goal_calories:.0f}kcal\n|{progress_bar(curr_calories, goal_calories)} {pct(curr_calories, goal_calories):2}%"
    )
    print(
        f"Duration: {curr_duration:.0f} / {goal_duration:.0f} min\n|{progress_bar(curr_duration, goal_duration)} {pct(curr_duration, goal_duration):2}%"
    )
    print(
        f"Rides: {curr_rides:.0f} / {goal_rides:.0f}\n|{progress_bar(curr_rides, goal_rides)} {pct(curr_rides, goal_rides):2}%"
    )
    print("")


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
        print_stats(df)

        # Monthly comparison
        df_monthly = df.groupby(df["date"].dt.to_period("M")).agg(
            distance_mean_km=("distance_km", "mean"),
            distance_sum_km=("distance_km", "sum"),
            power_mean_w=("power_w", "mean"),
            count=("date", "count"),
        )
        # ensure existance of all months in previous 12 months
        all_periods = pd.period_range(df["date"].iloc[-1] - pd.DateOffset(months=12), df["date"].iloc[-1], freq="M")
        df_monthly = df_monthly.reindex(all_periods, fill_value=0)

        print_charts(df_monthly)

        print_yearly_goals(df)

        # optional plotting of cumulative and monthly distance
        if plot_arg.lower() == "plot" and df.empty is False:
            plot_distance(df, df_monthly)
