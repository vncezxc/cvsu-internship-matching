import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        print(f"[CONNECT] room_name: {self.room_name}, room_group_name: {self.room_group_name}")
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        print(f"[DISCONNECT] room_group_name: {self.room_group_name}, channel_name: {self.channel_name}")
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        print(f"[RECEIVE] text_data: {text_data}")
        text_data_json = json.loads(text_data)
        msg_type = text_data_json.get('type', 'chat_message')
        if msg_type == 'chat_message':
            message = text_data_json.get('message', '')
            # Get the user from the scope
            user = self.scope['user']
            print(f"[RECEIVE] user: {user}, authenticated: {user.is_authenticated}, message: {message}")
            if user.is_authenticated and message:
                # Save message to database
                message_obj = await self.save_message(user, message)
                print(f"[RECEIVE] message_obj: {message_obj}")
                # Send message to room group
                if message_obj:
                    timestamp = message_obj.timestamp.strftime('%b %d, %Y, %I:%M %p')
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message': message,
                            'sender': user.username,
                            'sender_id': user.id,
                            'timestamp': timestamp,
                            'message_id': message_obj.id
                        }
                    )
        elif msg_type == 'typing':
            # Broadcast typing event to other users in the room
            user = self.scope['user']
            if user.is_authenticated:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing',
                        'user_id': user.id
                    }
                )
        # Ignore other message types for now
    
    # Receive message from room group
    async def chat_message(self, event):
        print(f"[CHAT_MESSAGE] event: {event}")
        message = event['message']
        sender = event['sender']
        sender_id = event['sender_id']
        timestamp = event['timestamp']
        message_id = event['message_id']
        # Get sender avatar
        sender_avatar = None
        from .models import User
        try:
            user = User.objects.get(id=sender_id)
            if hasattr(user, 'student_profile') and user.student_profile.avatar:
                sender_avatar = user.student_profile.avatar.url
            elif hasattr(user, 'adviser_profile') and user.adviser_profile.avatar:
                sender_avatar = user.adviser_profile.avatar.url
            elif hasattr(user, 'coordinator_profile') and user.coordinator_profile.avatar:
                sender_avatar = user.coordinator_profile.avatar.url
        except Exception as e:
            print(f"[CHAT_MESSAGE] Exception: {e}")
            sender_avatar = '/static/images/default_avatar.png'
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message,
            'sender': sender,
            'sender_id': sender_id,
            'timestamp': timestamp,
            'message_id': message_id,
            'sender_avatar': sender_avatar or '/static/images/default_avatar.png'
        }))
    
    # Handler for typing indicator
    async def typing(self, event):
        print(f"[TYPING] event: {event}")
        user_id = event['user_id']
        # Send typing event to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': user_id
        }))
    
    @database_sync_to_async
    def save_message(self, user, message_content):
        """Save the message to the database."""
        from .models import ChatRoom, Message
        try:
            # Get the chat room by ID instead of name
            room = ChatRoom.objects.get(id=self.room_name)
            print(f"[SAVE_MESSAGE] Found room by id: {room}")
            # Create and save the message
            message = Message.objects.create(
                room=room,
                sender=user,
                content=message_content
            )
            print(f"[SAVE_MESSAGE] Created message: {message}")
            # Mark as read by the sender
            message.read_by.add(user)
            return message
        except ChatRoom.DoesNotExist:
            print(f"[SAVE_MESSAGE] ChatRoom.DoesNotExist: {self.room_name}")
            return None