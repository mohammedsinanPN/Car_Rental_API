from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("cars/", views.CarListCreate.as_view(), name="cars"),
    path("cars/<int:pk>/", views.CarDetail.as_view(), name="car_detail"),
    path("available-cars/", views.AvailableCarsView.as_view(), name="available_cars"),
    path("bookings/", views.BookingListCreate.as_view(), name="bookings"),
    path("bookings/<int:pk>/", views.BookingDetail.as_view(), name="booking_detail"),
    path("bookings/<int:pk>/cancel/", views.BookingCancelView.as_view(), name="booking_cancel"),
    path("bookings/<int:pk>/status/", views.BookingStatusUpdate.as_view(), name="booking_status"),
    path("logout/", views.JWTLogout.as_view(), name="logout"),
]
