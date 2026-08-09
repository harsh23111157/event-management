from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.views import View

from .models import AuditLog


class AuditLogListView(LoginRequiredMixin, View):
    template_name = "audit/auditlog_list.html"
    paginate_by = 25

    def get(self, request):
        if not request.user.is_admin:
            raise PermissionDenied("Only Administrators can view system audit logs.")

        qs = AuditLog.objects.select_related("user").all()

        action = request.GET.get("action", "").strip()
        if action:
            qs = qs.filter(action__icontains=action)

        entity = request.GET.get("entity_type", "").strip()
        if entity:
            qs = qs.filter(entity_type__icontains=entity)

        search = request.GET.get("q", "").strip()
        if search:
            qs = qs.filter(
                Q(description__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )

        paginator = Paginator(qs, self.paginate_by)
        page = paginator.get_page(request.GET.get("page"))

        all_actions = AuditLog.objects.values_list("action", flat=True).distinct()
        all_entities = AuditLog.objects.values_list("entity_type", flat=True).distinct()

        return render(request, self.template_name, {
            "page_obj": page,
            "actions": sorted(set(a for a in all_actions if a)),
            "entities": sorted(set(e for e in all_entities if e)),
            "current_action": action,
            "current_entity": entity,
            "search_query": search,
        })
