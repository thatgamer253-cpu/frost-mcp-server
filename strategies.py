from enum import Enum

class SearchStrategy(Enum):
    SCOUT = "Scout"         # Passive: Notification only
    SNIPER = "Sniper"       # High Matching: Deep personalization, manual approval
    MACHINE_GUN = "Machine Gun" # High Volume: Quick application, automated

class StrategyManager:
    def __init__(self, strategy_type: SearchStrategy):
        self.strategy_type = strategy_type

    def get_thresholds(self):
        if self.strategy_type == SearchStrategy.SCOUT:
            return {"min_score": 70, "auto_apply": False}
        elif self.strategy_type == SearchStrategy.SNIPER:
            return {"min_score": 85, "auto_apply": False, "personalization_depth": "High"}
        elif self.strategy_type == SearchStrategy.MACHINE_GUN:
            return {"min_score": 60, "auto_apply": True, "personalization_depth": "Low"}
        return {"min_score": 80, "auto_apply": False}

    def should_apply(self, score):
        thresholds = self.get_thresholds()
        return score >= thresholds["min_score"] and thresholds["auto_apply"]

    def requires_approval(self, score):
        thresholds = self.get_thresholds()
        return score >= thresholds["min_score"] and not thresholds["auto_apply"]
