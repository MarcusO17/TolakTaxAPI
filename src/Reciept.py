from pydantic import BaseModel, Field, PositiveInt
from typing import List, Optional
from datetime import datetime
from decimal import Decimal # Let's decide to use Decimal

class Item(BaseModel):
    name: str = Field(..., description="Name of the item")
    quantity: PositiveInt = Field(..., description="Quantity of the item")
    unit_price: Decimal = Field(..., gt=Decimal(0), description="Price per unit")

class Merchant(BaseModel): # New idea: separate merchant
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None

class Receipt(BaseModel):
    receipt_id: Optional[str] = None
    merchant: Merchant
    transaction_date: datetime
    items: List[Item]
    subtotal: Decimal = Field(..., ge=Decimal(0))
    tax_amount: Decimal = Field(default=Decimal(0), ge=Decimal(0))
    total_amount: Decimal = Field(..., ge=Decimal(0))
    payment_method: str 
    currency: str = Field(default="USD", min_length=3, max_length=3)