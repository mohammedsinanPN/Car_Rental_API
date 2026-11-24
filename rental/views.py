
from datetime import date
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from .models import CarDb, BookingDb, UserRole
from .serializers import RegisterSerializer, CarSerializer, BookingSerializer, BookingStatusSerializer


class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return UserRole.objects.filter(user=request.user, role="admin").exists()


def is_admin_user(user):
    return UserRole.objects.filter(user=user, role="admin").exists()


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.user_role.role,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CarListCreate(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminRole()]
        return [permissions.AllowAny()]

    def get(self, request):
        cars = CarDb.objects.filter(is_available=True)
        serializer = CarSerializer(cars, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CarSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CarDetail(APIView):
    def get_permissions(self):
        if self.request.method in ["PUT", "DELETE"]:
            return [IsAdminRole()]
        return [permissions.AllowAny()]

    def get(self, request, pk):
        car = get_object_or_404(CarDb, pk=pk, is_available=True)
        return Response(CarSerializer(car).data)

    def put(self, request, pk):
        car = get_object_or_404(CarDb, pk=pk)
        serializer = CarSerializer(car, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        car = get_object_or_404(CarDb, pk=pk)
        car.is_available = False
        car.save()
        return Response({"message": "Car deactivated successfully."})


class AvailableCarsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        pickup = request.query_params.get("pickup_date")
        returned = request.query_params.get("return_date")
        if not pickup or not returned:
            return Response(
                {"error": "Provide pickup_date and return_date in YYYY-MM-DD format."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            pickup_date = date.fromisoformat(pickup)
            return_date = date.fromisoformat(returned)
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        if pickup_date < date.today() or return_date <= pickup_date:
            return Response({"error": "Enter valid future pickup and return dates."}, status=400)

        booked_car_ids = BookingDb.objects.filter(
            status__in=["Pending", "Approved"],
            pickup_date__lt=return_date,
            return_date__gt=pickup_date,
        ).values_list("car_id", flat=True)

        cars = CarDb.objects.filter(is_available=True).exclude(id__in=booked_car_ids)
        return Response(CarSerializer(cars, many=True).data)


class BookingListCreate(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if is_admin_user(request.user):
            bookings = BookingDb.objects.all().order_by("-created_date")
        else:
            bookings = BookingDb.objects.filter(user=request.user).order_by("-created_date")
        return Response(BookingSerializer(bookings, many=True).data)

    def post(self, request):
        serializer = BookingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BookingDetail(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_booking(self, request, pk):
        booking = get_object_or_404(BookingDb, pk=pk)
        if not is_admin_user(request.user) and booking.user_id != request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can access only your own bookings.")
        return booking

    def get(self, request, pk):
        booking = self.get_booking(request, pk)
        return Response(BookingSerializer(booking).data)


class BookingCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        booking = get_object_or_404(BookingDb, pk=pk)
        if not is_admin_user(request.user) and booking.user_id != request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can cancel only your own booking.")
        if booking.status not in ["Pending", "Approved"]:
            return Response({"error": "This booking cannot be cancelled."}, status=400)
        booking.status = "Cancelled"
        booking.save()
        return Response({"message": "Booking cancelled successfully."})


class BookingStatusUpdate(APIView):
    permission_classes = [IsAdminRole]

    def put(self, request, pk):
        booking = get_object_or_404(BookingDb, pk=pk)
        serializer = BookingStatusSerializer(booking, data=request.data)
        if serializer.is_valid():
            new_status = serializer.validated_data.get("status")
            if new_status == "Approved":
                overlapping = BookingDb.objects.filter(
                    car=booking.car,
                    status="Approved",
                    pickup_date__lt=booking.return_date,
                    return_date__gt=booking.pickup_date,
                ).exclude(pk=booking.pk)
                if overlapping.exists():
                    return Response({"error": "Another booking for this car is already approved for these dates."}, status=400)
            serializer.save()
            return Response(BookingSerializer(booking).data)
        return Response(serializer.errors, status=400)


class JWTLogout(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "Refresh token is required."}, status=400)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logged out successfully."})
        except TokenError:
            return Response({"error": "Invalid or expired refresh token."}, status=400)
