from rest_framework import serializers

from .models import HistorialOrden


class HistorialOrdenSerializer(serializers.ModelSerializer):
    tipo_evento_nombre = serializers.CharField(source="get_tipo_evento_display")
    usuario_nombre = serializers.SerializerMethodField()

    class Meta:
        model = HistorialOrden
        fields = (
            "id",
            "fecha",
            "tipo_evento",
            "tipo_evento_nombre",
            "usuario",
            "usuario_nombre",
            "detalle",
        )
        read_only_fields = fields

    def get_usuario_nombre(self, evento) -> str:
        if evento.usuario is None:
            return "Sistema"
        return evento.usuario.get_full_name() or evento.usuario.username
