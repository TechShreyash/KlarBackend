from pydantic import BaseModel, Field
from typing import List, Optional


# --- NEW: Sub-model for a single line item ---
# This defines the structure for one item in the invoice's item table.
# As per the prompt, this value will be converted to INR.
class LineItemSchema(BaseModel):
    product_name: str = Field(description="Name or description of the product/service.")
    quantity: int = Field(description="Quantity of the item.")
    unit_cost: float = Field(
        description="The cost for a single unit (Rate), converted to INR."
    )


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
        default=None,
        description="Canonical ID of the vendor, or null if a match isn't found.",
    )
    ship_to_address: Optional[str] = Field(
        description="Shipping address for the invoice."
    )
    date: Optional[str] = Field(description="Invoice date in YYYY-MM-DD format.")
    ship_mode: Optional[str] = Field(description="Shipping mode used for the invoice.")

    description: Optional[str] = Field(
        default=None, description="A short, one-sentence summary of the invoice."
    )

    line_items: List[LineItemSchema] = Field(
        description="A list of all items, products, or services on the invoice (monetary values in INR)."
    )

    extracted_currency: Optional[str] = Field(
        description="The original currency code or symbol found on the invoice (e.g., 'USD', '$', '₹')."
    )
    currency: str = Field(
        default="INR",
        description="The final currency of all monetary fields in this JSON, which must be INR.",
    )

    sub_total: float = Field(description="Subtotal amount, converted to INR.")
    discount: float = Field(
        default=0.0, description="Discount amount, converted to INR."
    )
    shipping_fee: float = Field(
        default=0.0, description="Shipping fee, converted to INR."
    )
    total_amount_payable: float = Field(
        description="Total amount payable, converted to INR."
    )

    human_verification_required: bool = Field(
        description="Flag indicating if human verification is needed."
    )
    human_verification_reason: Optional[str] = Field(
        default=None, description="Brief reason why human verification is required."
    )


# This model inherits the changes from InvoiceExtractionSchema automatically
class InvoiceResponseModel(InvoiceExtractionSchema):
    status: str = Field(description="Processing status of the invoice.")
    pdf_path: Optional[str] = Field(
        description="Path to the stored PDF of the invoice."
    )
    task_id: Optional[str] = Field(
        description="Unique task identifier for tracking invoice processing."
    )
    file_link: Optional[str] = Field(
        description="Publicly accessible link to download the invoice PDF."
    )
    auth_email: Optional[str] = Field(
        description="Email of the user who uploaded the invoice."
    )
