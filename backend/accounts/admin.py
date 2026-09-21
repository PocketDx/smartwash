from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class SmartWashUserAdmin(UserAdmin):
    list_display = ("username", "email", "rol", "is_active", "is_staff")
    list_filter = ("rol", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("SmartWash", {"fields": ("rol",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("SmartWash", {"fields": ("rol",)}),)
