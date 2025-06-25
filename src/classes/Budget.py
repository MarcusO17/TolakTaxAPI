from pydantic import BaseModel, Field
from typing import Dict, Optional

class UserBudgetData(BaseModel):
    budgets: Dict[str, Dict[str, float]]
    budget_period: Optional[str] = Field(None, alias="budgetPeriod")
