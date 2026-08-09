"""REST API for expenses."""
from django.urls import path
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import is_finance_or_admin
from apps.finance.models import Expense, ExpenseService


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ["id", "event", "description", "category", "amount", "status",
                  "created_by", "approved_by", "approved_at", "rejection_reason",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "status", "approved_by", "approved_at",
                            "rejection_reason", "created_at", "updated_at"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class ExpenseListCreateView(ListCreateAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.select_related("event", "created_by", "approved_by")

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        ser = ExpenseSerializer(data=data)
        ser.is_valid(raise_exception=True)
        expense = ser.save(created_by=request.user)
        return Response({"success": True, "id": expense.id}, status=status.HTTP_201_CREATED)


class ExpenseApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk)
        try:
            ExpenseService.approve(expense, request.user)
        except PermissionError as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"success": True, "status": expense.status})


class ExpenseRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk)
        reason = request.data.get("reason", "").strip()
        try:
            ExpenseService.reject(expense, request.user, reason)
        except PermissionError as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"success": True, "status": expense.status})


urlpatterns = [
    path("expenses/", ExpenseListCreateView.as_view(), name="api_expense_list"),
    path("expenses/<int:pk>/approve/", ExpenseApproveView.as_view(), name="api_expense_approve"),
    path("expenses/<int:pk>/reject/", ExpenseRejectView.as_view(), name="api_expense_reject"),
]
