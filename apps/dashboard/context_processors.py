def dashboard_nav_context(request):
    return {"nav_section": request.resolver_match.url_name if hasattr(request, "resolver_match") else ""}
