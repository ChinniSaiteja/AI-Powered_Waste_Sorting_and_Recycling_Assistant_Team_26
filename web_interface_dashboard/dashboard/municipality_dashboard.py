class MunicipalityDashboard:
    """
    Shows waste classification statistics for one region.

    All counting and percentages are done by DatabaseManager.get_stats();
    this class loads the data once and prepares it for the dashboard page.
    """

    # Order and colours of the category bars (names as stored in the database)
    CATEGORY_COLOURS = {
        "recyclable": "#2E7D5B",
        "compostable": "#C08A2E",
        "landfill": "#7A7A7A",
    }
    DEFAULT_COLOUR = "#90A4AE"

    # ------------------------------------------------------------------
    # 1. Constructor
    # ------------------------------------------------------------------
    def __init__(self, database_manager, region="Dortmund"):
        self._database_manager = database_manager
        self._region = None
        self.region = region  # the setter validates the value
        self._stats = None

    # ------------------------------------------------------------------
    # 2. Initialization method: load the data ONCE
    # ------------------------------------------------------------------
    def load_data(self):
        """Fetch the statistics for the region from the database (one call)."""
        self._stats = self._database_manager.get_stats(region=self._region)

    def _ensure_loaded(self):
        if self._stats is None:
            self.load_data()

    # ------------------------------------------------------------------
    # 3. Encapsulation: getters and setters
    # ------------------------------------------------------------------
    @property
    def region(self):
        return self._region

    @region.setter
    def region(self, region):
        # None means "all regions" (supported by DatabaseManager)
        if region is not None and (not isinstance(region, str) or not region.strip()):
            raise ValueError("Region must be a non-empty string or None (all regions).")
        self._region = region.strip() if region else None
        self._stats = None  # region changed -> data must be reloaded

    # ------------------------------------------------------------------
    # Key figures (no extra database call once loaded)
    # ------------------------------------------------------------------
    def get_dashboard_statistics(self):
        self._ensure_loaded()
        return self._stats

    def get_region_name(self):
        return self.get_dashboard_statistics()["region"]

    def get_total_analysed_items(self):
        return self.get_dashboard_statistics()["total_items"]

    def get_recyclable_percentage(self):
        """Share of items classified as recyclable, in percent."""
        return self.get_dashboard_statistics()["category_percentages"].get("recyclable", 0.0)

    def get_category_distribution(self):
        """One entry per category for the bars: name, percent, count, colour."""
        stats = self.get_dashboard_statistics()
        percentages = stats["category_percentages"]
        counts = stats["by_category"]
        ordered = list(self.CATEGORY_COLOURS) + [c for c in percentages if c not in self.CATEGORY_COLOURS]
        return [
            {
                "name": category.title(),
                "percent": round(percentages[category]),
                "count": counts.get(category, 0),
                "colour": self.CATEGORY_COLOURS.get(category, self.DEFAULT_COLOUR),
            }
            for category in ordered
            if category in percentages
        ]