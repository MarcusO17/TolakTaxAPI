from pydantic import BaseModel
from typing import Dict

class UserBudgetData(BaseModel):
    budgets: Dict[str, Dict[str, float]]
