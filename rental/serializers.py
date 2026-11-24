from datetime import date
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import CarDb, BookingDb, UserRole


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=["customer", "admin"], default="customer", write_only=True)
    admin_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "role", "admin_code"]

    def validate(self, validated_data):
        requested_role = validated_data.get("role", "customer")
        admin_code = validated_data.pop("admin_code", "")
        if requested_role == "admin":
            if not admin_code or admin_code != settings.ADMIN_REGISTRATION_CODE:
                raise serializers.ValidationError({"admin_code": "Valid admin registration code is required."})
        return validated_data

    def create(self, validated_data):
        role = validated_data.pop("role", "customer")
        user = User.objects.create_user(**validated_data)
        UserRole.objects.create(user=user, role=role)
        return user


class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarDb
        fields = "__all__"
        read_only_fields = ["id", "created_date"]


class BookingSerializer(serializers.ModelSerializer):
    car_name = serializers.CharField(source="car.car_name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = BookingDb
        fields = [
            "id", "user", "username", "car", "car_name",
            "pickup_date", "return_date", "pickup_location",
            "total_days", "total_amount", "status", "created_date",
        ]
        read_only_fields = [
            "id", "user", "username", "total_days", "total_amount",
            "status", "created_date",
        ]

    def validate(self, attrs):
        pickup = attrs.get("pickup_date")
        returned = attrs.get("return_date")
        car = attrs.get("car")

        if pickup and pickup < date.today():
            raise serializers.ValidationError("Pickup date cannot be in the past.")
        if pickup and returned and returned <= pickup:
            raise serializers.ValidationError("Return date must be after pickup date.")
        if car and not car.is_available:
            raise serializers.ValidationError("This car is not active for rental.")

        if car and pickup and returned:
            conflicts = BookingDb.objects.filter(
                car=car,
                status__in=["Pending", "Approved"],
                pickup_date__lt=returned,
                return_date__gt=pickup,
            )
            if self.instance:
                conflicts = conflicts.exclude(pk=self.instance.pk)
            if conflicts.exists():
                raise serializers.ValidationError("This car is already booked for the selected dates.")
        return attrs

    def create(self, validated_data):
        days = (validated_data["return_date"] - validated_data["pickup_date"]).days
        validated_data["total_days"] = days
        validated_data["total_amount"] = days * validated_data["car"].price_per_day
        return BookingDb.objects.create(**validated_data)


class BookingStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingDb
        fields = ["status"]
