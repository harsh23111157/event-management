from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.views import View

from .models import AuditLog


class AuditLogListView(LoginRequiredMixin, View):
    template_name = "audit/auditlog_list.html"
    paginate_by = 40

    def get(self, request):
        if not request.user.is_admin:
            return redirect("dashboard")
        qs = AuditLog.objects.select_related("user").all()
        action = request.GET.get("action")
        if action:
            qs = qs.filter(action__icontains=action)
        paginator = Paginator(qs, self.paginate_by)
        page = paginator.get_page(request.GET.get("page"))
        return render(request, self.template_name, {"page_obj": page, "actions": qs.values_list("action", flat=True).distinct()})
