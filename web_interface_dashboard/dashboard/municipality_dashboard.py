
class MunicipalityDashboard:

    def __init__(self, database_manager, region="Dortmund"):
        self.database_manager = database_manager
        self.region = region

    def get_total_analysed_items(self):
        stats = self.database_manager.get_stats(region=self.region)
        return stats["total_items"]

    def get_category_counts(self):
        stats = self.database_manager.get_stats(region=self.region)
        return stats["by_category"]

    def calculate_category_percentages(self):
        stats = self.database_manager.get_stats(region=self.region)
        return stats["category_percentages"]

    def get_dashboard_statistics(self):
        return self.database_manager.get_stats(region=self.region)

    def get_recent_classifications(self, limit=50):
        return self.database_manager.get_classification_records(
            region=self.region,
            limit=limit
        )
