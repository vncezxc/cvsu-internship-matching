from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.templatetags.static import static
from .models import ChatRoom, Message
from accounts.models import User, StudentProfile, AdviserProfile, CoordinatorProfile

# Create your views here.

# Student chat views
@login_required
def student_chats(request):
    """View all chats for a student."""
    if not request.user.is_student:
        messages.error(request, 'Only students can access student chats.')
        return redirect('dashboard:home')
    
    # Get all chat rooms for this student
    chat_rooms = request.user.chat_rooms.all()
    
    # Get adviser users
    try:
        profile = request.user.student_profile
        course = profile.course
        section = profile.section
        
        # Find advisers for this student's course and section
        advisers = AdviserProfile.objects.filter(courses=course)
        adviser_users = [adviser.user for adviser in advisers if section in adviser.get_sections_list()]
        
        context = {
            'chat_rooms': chat_rooms,
            'advisers': adviser_users,
        }
        return render(request, 'chat/student_chats.html', context)
    except StudentProfile.DoesNotExist:
        messages.warning(request, 'Please complete your profile first.')
        return redirect('accounts:edit_profile')

@login_required
def student_adviser_chat(request, adviser_id):
    """Chat between student and adviser."""
    if not request.user.is_student:
        messages.error(request, 'Only students can access student chats.')
        return redirect('dashboard:home')
    
    adviser = get_object_or_404(User, id=adviser_id, user_type=User.UserType.ADVISER)
    
    # Get or create chat room
    chat_room = ChatRoom.get_or_create_private_room(request.user, adviser)
    
    # Get messages for this room
    messages_list = Message.objects.filter(room=chat_room).order_by('timestamp')
    
    # Mark messages as read
    for message in messages_list:
        if message.sender != request.user:
            message.mark_as_read(request.user)
    
    # Get profile image for adviser
    try:
        avatar = adviser.adviser_profile.profile_image.url
    except Exception:
        avatar = static('images/default_avatar.png')
    
    # Compute initials for participant
    def get_initials(user):
        if user.first_name and user.last_name:
            return f"{user.first_name[0]}{user.last_name[0]}".upper()
        elif user.first_name:
            return user.first_name[0].upper()
        elif user.username:
            return user.username[0].upper()
        return "?"
    
    context = {
        'chat_room': chat_room,
        'messages': messages_list,
        'chat_title': adviser.get_full_name() or adviser.username,
        'chat_avatar': avatar,
        'current_user': request.user,
        'participant_name': adviser.get_full_name() or adviser.username,
        'participant_role': 'ADVISER',
        'participant_profile': adviser.adviser_profile if hasattr(adviser, 'adviser_profile') else None,
        'participant_initials': get_initials(adviser),
    }
    # Instead of rendering a custom template, redirect to the generic chat_room view for this room
    return redirect('chat:room', room_id=chat_room.id)

# Adviser chat views
@login_required
def adviser_chats(request):
    """View all chats for an adviser."""
    if not request.user.is_adviser:
        messages.error(request, 'Only OJT advisers can access adviser chats.')
        return redirect('dashboard:home')
    
    # Get all chat rooms for this adviser
    chat_rooms = request.user.chat_rooms.all()
    
    # Get student users
    try:
        profile = request.user.adviser_profile
        
        # Find students for this adviser's courses and sections
        students = StudentProfile.objects.filter(
            course__in=profile.courses.all(),
            section__in=profile.get_sections_list()
        )
        student_users = [student.user for student in students]
        
        # Get coordinator users
        coordinators = User.objects.filter(user_type=User.UserType.COORDINATOR)
        
        context = {
            'chat_rooms': chat_rooms,
            'students': student_users,
            'coordinators': coordinators,
        }
        return render(request, 'chat/adviser_chats.html', context)
    except:
        messages.warning(request, 'Your adviser profile is not set up.')
        return redirect('home')

@login_required
def adviser_student_chat(request, student_id):
    """Chat between adviser and student."""
    if not request.user.is_adviser:
        messages.error(request, 'Only OJT advisers can access adviser chats.')
        return redirect('dashboard:home')
    
    student = get_object_or_404(User, id=student_id, user_type=User.UserType.STUDENT)
    
    # Check if adviser has access to this student
    try:
        profile = request.user.adviser_profile
        student_profile = student.student_profile
        
        if not (student_profile.course in profile.courses.all() and 
                student_profile.section in profile.get_sections_list()):
            messages.error(request, 'You do not have access to this student.')
            return redirect('chat:adviser_chats')
        
        # Get or create chat room
        chat_room = ChatRoom.get_or_create_private_room(request.user, student)
        
        # Get messages for this room
        messages_list = Message.objects.filter(room=chat_room).order_by('timestamp')
        
        # Mark messages as read
        for message in messages_list:
            if message.sender != request.user:
                message.mark_as_read(request.user)
        
        try:
            avatar = student.student_profile.profile_image.url
        except Exception:
            avatar = static('images/default_avatar.png')
        context = {
            'chat_room': chat_room,
            'messages': messages_list,
            'chat_title': student.get_full_name() or student.username,
            'chat_avatar': avatar,
            'current_user': request.user,
        }
        # Instead of rendering a custom template, redirect to the generic chat_room view for this room
        return redirect('chat:room', room_id=chat_room.id)
    except:
        messages.warning(request, 'Your adviser profile is not set up.')
        return redirect('home')

@login_required
def adviser_coordinator_chat(request, coordinator_id):
    """Chat between adviser and coordinator."""
    if not request.user.is_adviser:
        messages.error(request, 'Only OJT advisers can access adviser chats.')
        return redirect('dashboard:home')
    
    coordinator = get_object_or_404(User, id=coordinator_id, user_type=User.UserType.COORDINATOR)
    
    # Get or create chat room
    chat_room = ChatRoom.get_or_create_private_room(request.user, coordinator)
    
    # Get messages for this room
    messages_list = Message.objects.filter(room=chat_room).order_by('timestamp')
    
    # Mark messages as read
    for message in messages_list:
        if message.sender != request.user:
            message.mark_as_read(request.user)
    
    try:
        avatar = coordinator.coordinator_profile.avatar.url
    except Exception:
        avatar = static('images/default_avatar.png')
    context = {
        'chat_room': chat_room,
        'messages': messages_list,
        'chat_title': coordinator.get_full_name() or coordinator.username,
        'chat_avatar': avatar,
        'current_user': request.user,
    }
    return render(request, 'chat/adviser_coordinator_chat.html', context)

# Coordinator chat views
@login_required
def coordinator_chats(request):
    """View all chats for a coordinator."""
    if not request.user.is_coordinator:
        messages.error(request, 'Only OJT coordinators can access coordinator chats.')
        return redirect('dashboard:home')
    
    # Get all chat rooms for this coordinator
    chat_rooms = request.user.chat_rooms.all()
    
    # Get adviser users
    advisers = User.objects.filter(user_type=User.UserType.ADVISER)
    
    rooms_info = []
    for room in chat_rooms:
        other = room.get_other_participant(request.user)
        avatar = room.get_other_participant_avatar(request.user)
        name = room.get_other_participant_name(request.user)
        last_message = room.get_last_message()
        unread_count = room.get_unread_count(request.user)
        rooms_info.append({
            'id': room.id,
            'name': name,
            'avatar': avatar,
            'last_message': last_message,
            'unread_count': unread_count,
            'room': room,
        })
    context = {
        'rooms_info': rooms_info,
        'advisers': advisers,
    }
    return render(request, 'chat/coordinator_chats.html', context)

@login_required
def coordinator_adviser_chat(request, adviser_id):
    """Chat between coordinator and adviser."""
    if not request.user.is_coordinator:
        messages.error(request, 'Only OJT coordinators can access coordinator chats.')
        return redirect('dashboard:home')
    
    adviser = get_object_or_404(User, id=adviser_id, user_type=User.UserType.ADVISER)
    
    # Get or create chat room
    chat_room = ChatRoom.get_or_create_private_room(request.user, adviser)
    
    # Get messages for this room
    messages_list = Message.objects.filter(room=chat_room).order_by('timestamp')
    
    # Mark messages as read
    for message in messages_list:
        if message.sender != request.user:
            message.mark_as_read(request.user)
    
    try:
        avatar = adviser.adviser_profile.avatar.url
    except Exception:
        avatar = static('images/default_avatar.png')
    context = {
        'room': chat_room,  # changed from 'chat_room' to 'room'
        'messages': messages_list,
        'chat_title': adviser.get_full_name() or adviser.username,
        'chat_avatar': avatar,
        'current_user': request.user,
    }
    return render(request, 'chat/coordinator_adviser_chat.html', context)

@login_required
def chat_list(request):
    """Messenger-like chat list for all users."""
    chat_rooms = request.user.chat_rooms.all()
    rooms_info = []
    for room in chat_rooms:
        other = room.get_other_participant(request.user)
        avatar = room.get_other_participant_avatar(request.user)
        name = room.get_other_participant_name(request.user)
        last_message = room.get_last_message()
        unread_count = room.get_unread_count(request.user)
        rooms_info.append({
            'id': room.id,
            'name': name,
            'avatar': avatar,
            'last_message': last_message,
            'unread_count': unread_count,
            'room': room,
        })
    context = {
        'rooms_info': rooms_info,
        'active_room': None,
    }
    # Add students (for advisers) and advisers (for coordinators) to context for new chat modal
    students = []
    advisers = []
    coordinators = []
    if request.user.is_adviser:
        # All students this adviser advises (by course and section)
        profile = getattr(request.user, 'adviser_profile', None)
        if profile:
            students = User.objects.filter(
                user_type=User.UserType.STUDENT,
                student_profile__course__in=profile.courses.all(),
                student_profile__section__in=profile.get_sections_list()
            )
    if request.user.is_coordinator:
        # All advisers in the system
        advisers = User.objects.filter(user_type=User.UserType.ADVISER)
    if request.user.is_student:
        # All advisers for this student's course and section
        profile = getattr(request.user, 'student_profile', None)
        if profile:
            advisers = User.objects.filter(
                user_type=User.UserType.ADVISER,
                adviser_profile__courses=profile.course,
                adviser_profile__sections__icontains=profile.section
            )
        # Students should NOT see coordinators in their chat list
        coordinators = User.objects.none()
    else:
        # All coordinators for other users
        coordinators = User.objects.filter(user_type=User.UserType.COORDINATOR)
    context.update({
        'students': students,
        'advisers': advisers,
        'coordinators': coordinators,
    })
    return render(request, 'chat/chat_list.html', context)

@login_required
def chat_room(request, room_id):
    """Generic Messenger-like chat room view by room id."""
    room = get_object_or_404(ChatRoom, id=room_id)
    if request.user not in room.participants.all():
        messages.error(request, 'You do not have access to this chat room.')
        return redirect('chat:chat_list')
    messages_list = Message.objects.filter(room=room).order_by('timestamp')
    other = room.get_other_participant(request.user)
    avatar = room.get_other_participant_avatar(request.user)
    name = room.get_other_participant_name(request.user)
    context = {
        'room': room,
        'messages': messages_list,
        'chat_title': name,
        'chat_avatar': avatar,
        'current_user': request.user,
        'hide_django_messages': True,
    }
    return render(request, 'chat/chat_room.html', context)

# API endpoints for AJAX
@login_required
def api_get_messages(request, room_name):
    """API endpoint to get messages for a chat room."""
    try:
        chat_room = ChatRoom.objects.get(name=room_name)
        
        # Check if user has access to this room
        if request.user not in chat_room.participants.all():
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        # Get messages after a certain timestamp
        after = request.GET.get('after')
        if after:
            after_timestamp = timezone.datetime.fromtimestamp(float(after), tz=timezone.utc)
            messages_list = Message.objects.filter(room=chat_room, timestamp__gt=after_timestamp)
        else:
            messages_list = Message.objects.filter(room=chat_room)
        
        # Format messages
        messages_data = []
        for message in messages_list.order_by('timestamp'):
            messages_data.append({
                'id': message.id,
                'sender': message.sender.username,
                'sender_id': message.sender.id,
                'content': message.content,
                'timestamp': message.timestamp.timestamp(),
                'is_read': message.is_read,
            })
        
        return JsonResponse({'messages': messages_data})
    except ChatRoom.DoesNotExist:
        return JsonResponse({'error': 'Chat room not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_mark_message_read(request, message_id):
    """API endpoint to mark a message as read."""
    try:
        message = Message.objects.get(id=message_id)
        
        # Check if user has access to this message
        if request.user not in message.room.participants.all():
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        # Mark message as read
        message.mark_as_read(request.user)
        
        return JsonResponse({'success': True})
    except Message.DoesNotExist:
        return JsonResponse({'error': 'Message not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def new_chat(request):
    """Handle starting a new chat from the chat list modal."""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if not user_id:
            messages.error(request, 'Please select a user to chat with.')
            return redirect('chat:chat_list')
        try:
            other_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('chat:chat_list')
        # Get or create the private chat room
        room = ChatRoom.get_or_create_private_room(request.user, other_user)
        return redirect('chat:room', room_id=room.id)
    else:
        return redirect('chat:chat_list')
