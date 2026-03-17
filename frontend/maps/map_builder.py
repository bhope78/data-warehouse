"""Folium map generation for choropleth visualizations."""

import folium


def create_base_map(center: tuple = (39.8283, -98.5795), zoom: int = 4) -> folium.Map:
    """Create a base US map centered on the continental US."""
    return folium.Map(location=center, zoom_start=zoom, tiles="CartoDB positron")


# TODO: Add choropleth layers for:
# - Salary-to-cost-of-living ratio
# - Housing affordability
# - Crime rates
# - Quality of life composite score
