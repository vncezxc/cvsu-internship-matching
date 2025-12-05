from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Student chat views
    path('student/', views.student_chats, name='student_chats'),
    path('student/<int:adviser_id>/', views.student_adviser_chat, name='student_adviser_chat'),
    
    # Adviser chat views
    path('adviser/', views.adviser_chats, name='adviser_chats'),
    path('adviser/student/<int:student_id>/', views.adviser_student_chat, name='adviser_student_chat'),
    path('adviser/coordinator/<int:coordinator_id>/', views.adviser_coordinator_chat, name='adviser_coordinator_chat'),
    
    # Coordinator chat views
    path('coordinator/', views.coordinator_chats, name='coordinator_chats'),
    path('coordinator/adviser/<int:adviser_id>/', views.coordinator_adviser_chat, name='coordinator_adviser_chat'),

    # Start a new chat (POST)
    path('new/', views.new_chat, name='new_chat'),
    # Messenger-like chat list (for all users)
    path('list/', views.chat_list, name='chat_list'),
    # Generic chat room by room id
    path('room/<int:room_id>/', views.chat_room, name='room'),
    # API endpoints for AJAX
    path('api/messages/<str:room_name>/', views.api_get_messages, name='api_get_messages'),
    path('api/mark-read/<int:message_id>/', views.api_mark_message_read, name='api_mark_message_read'),
]