from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd


def infer_name_column(columns: list[str] | pd.Index, preferred: tuple[str, ...] = ()) -> str | None:
    lowered = {str(column).lower(): str(column) for column in columns}
    for candidate in preferred:
        match = lowered.get(candidate.lower())
        if match:
            return match

    exact_candidates = (
        "lnrs_name",
        "name",
        "strategy_name",
        "area_name",
        "site_name",
    )
    for candidate in exact_candidates:
        match = lowered.get(candidate)
        if match:
            return match

    for column in columns:
        text = str(column).lower()
        if text.endswith("name") or text.endswith("_name") or text.endswith("nm"):
            return str(column)
    return None


def attach_geography_name(
    frame: gpd.GeoDataFrame,
    geography_path: Path,
    *,
    join_key: str,
    output_column: str,
    name_column: str | None = None,
) -> gpd.GeoDataFrame:
    if not geography_path.exists():
        enriched = frame.copy()
        enriched[output_column] = pd.NA
        return enriched

    geography = gpd.read_file(geography_path)
    chosen_name_column = name_column or infer_name_column(geography.columns)
    if chosen_name_column is None:
        enriched = frame.copy()
        enriched[output_column] = pd.NA
        return enriched

    working = frame.copy()
    working["geometry"] = working.geometry.representative_point()
    geography = geography.to_crs(working.crs) if geography.crs != working.crs else geography
    joined = gpd.sjoin(
        working[[join_key, "geometry"]],
        geography[[chosen_name_column, "geometry"]],
        how="left",
        predicate="within",
    ).drop(columns=["index_right"])
    return frame.merge(
        joined[[join_key, chosen_name_column]].rename(columns={chosen_name_column: output_column}),
        on=join_key,
        how="left",
    )


def summarize_named_geography(
    frame: pd.DataFrame,
    *,
    name_column: str,
    score_column: str,
    top_n: int = 10,
) -> pd.DataFrame:
    subset = frame[frame[name_column].notna()].copy()
    if subset.empty:
        return pd.DataFrame(
            columns=[
                name_column,
                "cell_count",
                "share_pct",
                "scenario_score_mean",
                "scenario_score_max",
            ]
        )

    summary = (
        subset.groupby(name_column, as_index=False)
        .agg(
            cell_count=("hex_id", "count"),
            scenario_score_mean=(score_column, "mean"),
            scenario_score_max=(score_column, "max"),
        )
        .sort_values(["cell_count", "scenario_score_max", name_column], ascending=[False, False, True])
        .reset_index(drop=True)
    )
    summary["share_pct"] = summary["cell_count"] / len(frame) * 100
    return summary.head(top_n)


def dominant_name_by_group(
    frame: pd.DataFrame,
    *,
    group_column: str,
    name_column: str,
    score_column: str,
    primary_output_column: str,
    list_output_column: str,
    count_output_column: str,
) -> pd.DataFrame:
    subset = frame[frame[name_column].notna()].copy()
    if subset.empty:
        return pd.DataFrame(
            columns=[group_column, primary_output_column, list_output_column, count_output_column]
        )

    counts = (
        subset.groupby([group_column, name_column], as_index=False)
        .agg(
            cell_count=("hex_id", "count"),
            scenario_score_max=(score_column, "max"),
        )
        .sort_values(
            [group_column, "cell_count", "scenario_score_max", name_column],
            ascending=[True, False, False, True],
        )
    )

    primary = counts.drop_duplicates(group_column)[[group_column, name_column]].rename(
        columns={name_column: primary_output_column}
    )
    counted = counts.groupby(group_column, as_index=False).agg(
        **{count_output_column: (name_column, "nunique")}
    )
    listed = (
        counts.groupby(group_column)[name_column]
        .apply(lambda values: " | ".join(dict.fromkeys(values)))
        .rename(list_output_column)
        .reset_index()
    )
    return primary.merge(listed, on=group_column, how="left").merge(counted, on=group_column, how="left")
