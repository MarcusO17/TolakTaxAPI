from pydantic import BaseModel, Field
from typing import List, Optional

class AchievementProgress(BaseModel):
    achievement_id: str = Field(alias="achievementId")
    progress: float
    is_completed: bool = Field(alias="isCompleted")


class UserAchievementsData(BaseModel):
    total_points: int = Field(alias="totalPoints")
    progress: List[AchievementProgress]
    current_scan_streak: Optional[int] = Field(None, alias="currentScanStreak")
    last_scan_timestamp: Optional[str] = Field(None, alias="lastScanTimestamp") 