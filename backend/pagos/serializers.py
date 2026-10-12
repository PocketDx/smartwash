from decimal import Decimal

from rest_framework import serializers

from .models import Pago


class PagoSerializer(serializers.ModelSerializer):
    monto = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        error_messages={"min_value": "El monto debe ser mayor que 0."},
    )
    metodo = serializers.ChoiceField(
        choices=Pago.Metodo.choices,
        error_messages={"invalid_choice": "El metodo debe ser efectivo, transferencia o tarjeta."},
    )

    class Meta:
        model = Pago
        fields = ("id", "monto", "metodo", "creado_en", "creado_por")
        read_only_fields = ("creado_en", "creado_por")
