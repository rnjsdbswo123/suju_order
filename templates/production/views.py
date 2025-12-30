from django.views.generic import TemplateView

class ProductionStatusView(TemplateView):
    template_name = 'production/status.html'