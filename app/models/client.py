from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class Client(Base):
    """
    Client-specific data for organizations that consume services.

    Attributes:
        contract_number: Unique contract identifier
        billing_info: JSON field with billing details
        payment_terms: Text field describing payment terms
    """
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True)
    contract_number = Column(String(50), nullable=True)
    billing_info = Column(JSON, nullable=True)  # e.g., {"billing_address": "...", "tax_id": "...", "payment_method": "..."}
    payment_terms = Column(Text, nullable=True)  # e.g., "Net 30", "Prepaid", etc.
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization", back_populates="client")

    def __repr__(self):
        return f"<Client(id={self.id}, organization_id={self.organization_id}, contract={self.contract_number})>"
