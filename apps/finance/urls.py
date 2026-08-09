from django.urls import path

from .views import (ExpenseApproveView, ExpenseCreateView,
                     ExpenseListView, ExpenseRejectView)

urlpatterns = [
    path("", ExpenseListView.as_view(), name="expense_list"),
    path("new/", ExpenseCreateView.as_view(), name="expense_create"),
    path("<int:pk>/approve/", ExpenseApproveView.as_view(), name="expense_approve"),
    path("<int:pk>/reject/", ExpenseRejectView.as_view(), name="expense_reject"),
]
