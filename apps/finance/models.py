"""Expense model and ExpenseService."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.events.models import Event


class ExpenseCategory(models.TextChoices):
    CATERING = "CATERING", "Catering"
    TRANSPORT = "TRANSPORT", "Transport"
    DECORATION = "DECORATION", "Decoration"
    PHOTOGRAPHY = "PHOTOGRAPHY", "Photography"
    PRINTING = "PRINTING", "Printing"
    EQUIPMENT = "EQUIPMENT", "Equipment Rental"
    OTHER = "OTHER", "Other"


class ExpenseStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class Expense(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="expenses")
    description = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=ExpenseCategory.choices, default=ExpenseCategory.OTHER)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, related_name="created_expenses")
    status = models.CharField(max_length=20, choices=ExpenseStatus.choices, default=ExpenseStatus.PENDING)
    rejection_reason = models.TextField(blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name="approved_expenses")
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="expense_amount_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.description} ({self.amount})"

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "Amount must be greater than zero."})
        if self.status == ExpenseStatus.REJECTED and not self.rejection_reason:
            raise ValidationError({"rejection_reason": "A reason is required when rejecting an expense."})


class ExpenseService:
    @staticmethod
    @transaction.atomic
    def approve(expense: Expense, user) -> Expense:
        from apps.audit.services import AuditService
        from apps.accounts.permissions import is_finance_or_admin
        if not is_finance_or_admin(user):
            raise PermissionError("Only Finance or Admin users can approve expenses.")
        if expense.status != ExpenseStatus.PENDING:
            raise ValueError("Only pending expenses can be approved.")
        expense.status = ExpenseStatus.APPROVED
        expense.approved_by = user
        from django.utils import timezone
        expense.approved_at = timezone.now()
        expense.save()
        AuditService.log(user, "EXPENSE_APPROVE", "expense", expense.id,
                         f"Approved expense '{expense.description}' for {expense.event.name}")
        return expense

    @staticmethod
    @transaction.atomic
    def reject(expense: Expense, user, reason: str) -> Expense:
        from apps.audit.services import AuditService
        from apps.accounts.permissions import is_finance_or_admin
        if not is_finance_or_admin(user):
            raise PermissionError("Only Finance or Admin users can reject expenses.")
        if not reason or not reason.strip():
            raise ValueError("A reason is required when rejecting an expense.")
        if expense.status != ExpenseStatus.PENDING:
            raise ValueError("Only pending expenses can be rejected.")
        expense.status = ExpenseStatus.REJECTED
        expense.rejection_reason = reason.strip()
        expense.save()
        AuditService.log(user, "EXPENSE_REJECT", "expense", expense.id,
                         f"Rejected expense '{expense.description}': {reason}")
        return expense
