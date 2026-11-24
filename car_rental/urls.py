
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rental import views

urlpatterns = [

    # User Registration
    path('register/', views.RegisterView.as_view()),

    # JWT Authentication
    path('jwt_login/', TokenObtainPairView.as_view()),
    path('refresh/', TokenRefreshView.as_view()),

    # Car APIs
    path('cars/', views.CarListCreate.as_view()),
    path('cars/<int:pk>/', views.CarDetail.as_view()),

    # Available Cars
    path('available-cars/', views.AvailableCarsView.as_view()),

    # Booking APIs
    path('bookings/', views.BookingListCreate.as_view()),
    path('bookings/<int:pk>/', views.BookingDetail.as_view()),

    # Cancel Booking
    path('bookings/<int:pk>/cancel/', views.BookingCancelView.as_view()),

    # Update Booking Status (Admin)
    path('bookings/<int:pk>/status/', views.BookingStatusUpdate.as_view()),

    # Logout
    path('logout/', views.JWTLogout.as_view()),

]
