# schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional


class InvoiceExtractionSchema(BaseModel):
    invoice_id: str = Field(description="Unique identifier for the invoice.")
    order_id: Optional[str] = Field(
        description="Order identifier associated with the invoice."
    )
    customer_name: Optional[str] = Field(
        description="Name of the customer being billed."
    )
    extracted_vendor_name: Optional[str] = Field(
        description="Name of the vendor sending the invoice."
    )
    canonical_vendor_id: Optional[str] = Field(
        description="Canonical ID of the vendor."
    )
    ship_to_address: Optional[str] = Field(
        description="Shipping address for the invoice."
    )
    date: Optional[str] = Field(description="Invoice date in YYYY-MM-DD format.")
    ship_mode: Optional[str] = Field(description="Shipping mode used for the invoice.")
    product_id: Optional[str] = Field(description="Normalized Product ID.")
    product_name: Optional[str] = Field(description="Name/description of the product.")

    quantity: int = Field(description="Quantity of the product.")

    unit_cost: float = Field(description="Unit cost of the product.")
    currency: Optional[str] = Field(description="3-letter ISO currency code.")
    sub_total: float = Field(description="Subtotal amount before discounts and fees.")
    discount: float = Field(description="Discount amount applied to the subtotal.")
    shipping_fee: float = Field(description="Shipping fee for the invoice.")
    total_amount_payable: float = Field(
        description="Total amount payable for the invoice."
    )
    human_verification_required: bool = Field(
        description="Flag indicating if human verification is needed."
    )
