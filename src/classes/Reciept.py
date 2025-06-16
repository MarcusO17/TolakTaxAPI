from typing import List, Optional
from pydantic import BaseModel, Field

class LineItem(BaseModel):
    description: str 
    quantity: float = Field(default=float("1.0"), gt=float("0"))
    original_unit_price: float = Field(ge=float("0"))
    line_item_discount_amount: Optional[float] = Field(default=None, ge=float("0"))
    line_item_discount_description: Optional[str] = None
    total_price: float = Field(ge=float("0")) # Price after line-item discount

class OverallDiscount(BaseModel):
    description: str
    amount: float

class Receipt(BaseModel):
    merchant_name: str
    merchant_address: Optional[str] = None
    transaction_datetime:  str # ISO 8601 format 
    line_items: List[LineItem] = Field(default_factory=list)
    
    subtotal: Optional[float] = Field(default=None, ge=float("0")) # Sum of line_items.total_price
    overall_discounts: Optional[List[OverallDiscount]] = Field(default_factory=list)
    tax_amount: Optional[float] = Field(default=None, ge=float("0"))
    total_amount: float # The final amount paid
    
    currency_code: Optional[str] = None # ISO 4217
    payment_method: Optional[str] = None
    expense_category: Optional[str] = None # Data enrichment