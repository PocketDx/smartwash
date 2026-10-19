from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from .models import Material, NivelDificultad, Servicio, Tarifa, TipoPrenda


class ConAutoriaSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        instancia = self.Meta.model(**validated_data)
        instancia.registrar_autoria(self.context["request"].user)
        instancia.save()
        return instancia

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.registrar_autoria(self.context["request"].user)
        instance.save()
        return instance


class NombreUnicoMixin:
    """El indice unico de la base distingue mayusculas; "Lavado" y "lavado"
    serian dos servicios distintos para ella, pero no para el administrador."""

    def validate_nombre(self, nombre):
        nombre = nombre.strip()
        repetidos = self.Meta.model.objects.filter(nombre__iexact=nombre)
        if self.instance is not None:
            repetidos = repetidos.exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise serializers.ValidationError(f'Ya existe "{nombre}" en el catalogo.')
        return nombre


class ServicioSerializer(NombreUnicoMixin, ConAutoriaSerializer):
    class Meta:
        model = Servicio
        fields = ("id", "nombre", "descripcion")


class TipoPrendaSerializer(NombreUnicoMixin, ConAutoriaSerializer):
    peso_estandar = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal("0.01"), required=False, allow_null=True
    )

    class Meta:
        model = TipoPrenda
        fields = ("id", "nombre", "peso_estandar")


class NivelDificultadSerializer(NombreUnicoMixin, ConAutoriaSerializer):
    factor = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal("0.01"))

    class Meta:
        model = NivelDificultad
        fields = ("id", "nombre", "factor")


class MaterialSerializer(NombreUnicoMixin, ConAutoriaSerializer):
    nivel_dificultad = serializers.PrimaryKeyRelatedField(queryset=NivelDificultad.objects.all())
    nivel_dificultad_nombre = serializers.CharField(source="nivel_dificultad.nombre", read_only=True)
    factor = serializers.DecimalField(
        source="nivel_dificultad.factor", max_digits=5, decimal_places=2, read_only=True
    )

    class Meta:
        model = Material
        fields = ("id", "nombre", "nivel_dificultad", "nivel_dificultad_nombre", "factor")


class TarifaSerializer(ConAutoriaSerializer):
    tipo_prenda = serializers.PrimaryKeyRelatedField(
        queryset=TipoPrenda.objects.all(), required=False, allow_null=True, default=None
    )
    tipo_prenda_nombre = serializers.CharField(
        source="tipo_prenda.nombre", read_only=True, allow_null=True
    )
    servicio_nombre = serializers.CharField(source="servicio.nombre", read_only=True)
    valor_base = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    precio_por_kilo = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    plazo_entrega_dias = serializers.IntegerField(min_value=1)

    class Meta:
        model = Tarifa
        fields = (
            "id",
            "servicio",
            "servicio_nombre",
            "tipo_prenda",
            "tipo_prenda_nombre",
            "valor_base",
            "precio_por_kilo",
            "plazo_entrega_dias",
            "vigente_desde",
            "vigente_hasta",
        )
        # DRF traduciria la restriccion de "una vigente por par" en un rechazo,
        # y aqui registrar una tarifa nueva debe cerrar la anterior.
        validators = []

    def validate(self, attrs):
        if self.instance is not None:
            for campo in ("tipo_prenda", "servicio"):
                if campo in attrs and attrs[campo] != getattr(self.instance, campo):
                    raise serializers.ValidationError(
                        {campo: "No se puede cambiar; registre una tarifa nueva."}
                    )

        desde = attrs.get("vigente_desde", getattr(self.instance, "vigente_desde", None))
        hasta = attrs.get("vigente_hasta", getattr(self.instance, "vigente_hasta", None))
        if hasta is not None and hasta <= desde:
            raise serializers.ValidationError(
                {"vigente_hasta": "Debe ser posterior a la fecha de inicio."}
            )

        vigente = self._tarifa_vigente(attrs)
        if vigente is not None and hasta is None:
            if self.instance is not None:
                raise serializers.ValidationError(
                    {"vigente_hasta": "Ya hay otra tarifa vigente para esta prenda y servicio."}
                )
            if desde <= vigente.vigente_desde:
                raise serializers.ValidationError(
                    {
                        "vigente_desde": "Debe ser posterior al inicio de la tarifa "
                        f"vigente ({vigente.vigente_desde})."
                    }
                )

        cruzada = self._tarifa_cruzada(attrs, desde, hasta, vigente if hasta is None else None)
        if cruzada is not None:
            hasta_cruzada = cruzada.vigente_hasta or "hoy en adelante"
            raise serializers.ValidationError(
                {
                    "vigente_desde": "El periodo se cruza con otra tarifa de esta prenda y "
                    f"servicio ({cruzada.vigente_desde} a {hasta_cruzada})."
                }
            )
        return attrs

    def _tarifa_cruzada(self, attrs, desde, hasta, a_cerrar):
        """Rangos [desde, hasta), con hasta vacio como infinito. La vigente que
        una tarifa nueva abierta va a cerrar no cuenta como cruce."""
        tipo_prenda = attrs.get("tipo_prenda", getattr(self.instance, "tipo_prenda", None))
        servicio = attrs.get("servicio", getattr(self.instance, "servicio", None))
        otras = Tarifa.objects.filter(tipo_prenda=tipo_prenda, servicio=servicio)
        if self.instance is not None:
            otras = otras.exclude(pk=self.instance.pk)
        if self.instance is None and a_cerrar is not None:
            otras = otras.exclude(pk=a_cerrar.pk)
        if hasta is not None:
            otras = otras.filter(vigente_desde__lt=hasta)
        return (
            otras.filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gt=desde))
            .order_by("vigente_desde")
            .first()
        )

    def _tarifa_vigente(self, attrs):
        tipo_prenda = attrs.get("tipo_prenda", getattr(self.instance, "tipo_prenda", None))
        servicio = attrs.get("servicio", getattr(self.instance, "servicio", None))
        vigentes = Tarifa.objects.filter(
            tipo_prenda=tipo_prenda, servicio=servicio, vigente_hasta__isnull=True
        )
        if self.instance is not None:
            vigentes = vigentes.exclude(pk=self.instance.pk)
        return vigentes.first()

    @transaction.atomic
    def create(self, validated_data):
        if validated_data.get("vigente_hasta") is None:
            anterior = (
                Tarifa.objects.select_for_update()
                .filter(
                    tipo_prenda=validated_data.get("tipo_prenda"),
                    servicio=validated_data["servicio"],
                    vigente_hasta__isnull=True,
                )
                .first()
            )
            if anterior is not None:
                anterior.vigente_hasta = validated_data["vigente_desde"]
                anterior.registrar_autoria(self.context["request"].user)
                anterior.save()
        return super().create(validated_data)
