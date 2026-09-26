from django.contrib import admin


class AutoriaAdminMixin(admin.ModelAdmin):
    readonly_fields = ("creado_por", "creado_en", "actualizado_por", "actualizado_en")

    def save_model(self, request, obj, form, change):
        obj.registrar_autoria(request.user)
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instancias = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for obj in instancias:
            if hasattr(obj, "registrar_autoria"):
                obj.registrar_autoria(request.user)
            obj.save()
        formset.save_m2m()
