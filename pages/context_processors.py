from .models import FormField, BaseFormField


def form_fields(request):
    """Контекстный процессор для полей формы"""
    return {
        'form_fields': FormField.objects.filter(is_active=True),
        'base_form_fields': BaseFormField.objects.filter(is_active=True).order_by('order')
    }

