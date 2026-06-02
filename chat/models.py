import os
from django.db import models
from django.utils import timezone
from accounts.models import User

class ChatRoom(models.Model):
    """Model for chat rooms between users."""
    
    name = models.CharField(max_length=255, unique=True)
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def get_last_message(self):
        """Get the last message in this chat room."""
        return self.messages.order_by('-timestamp').first()
    
    def get_unread_count(self, user):
        """Get the count of unread messages for a user."""
        if not user:
            return 0
        return self.messages.exclude(read_by=user).exclude(sender=user).count()

    def get_other_participant(self, user):
        """Return the other participant in a private chat room."""
        return self.participants.exclude(id=user.id).first()

    def get_other_participant_avatar(self, user):
        """Get the avatar URL of the other participant."""
        other = self.get_other_participant(user)
        if not other:
            return None
        if hasattr(other, 'student_profile') and hasattr(other.student_profile, 'profile_image') and other.student_profile.profile_image:
            return other.student_profile.profile_image.url
        if hasattr(other, 'adviser_profile') and hasattr(other.adviser_profile, 'profile_image') and other.adviser_profile.profile_image:
            return other.adviser_profile.profile_image.url
        if hasattr(other, 'coordinator_profile') and hasattr(other.coordinator_profile, 'profile_image') and other.coordinator_profile.profile_image:
            return other.coordinator_profile.profile_image.url
        return '/static/images/default_avatar.png'

    def get_other_participant_name(self, user):
        """Get the full name or username of the other participant."""
        other = self.get_other_participant(user)
        if not other:
            return "Unknown"
        return other.get_full_name() or other.username

    @classmethod
    def get_or_create_private_room(cls, user1, user2):
        """Get or create a private chat room between two users."""
        # Create a consistent room name based on user IDs
        users = sorted([user1.id, user2.id])
        room_name = f"private_{users[0]}_{users[1]}"
        
        try:
            room = cls.objects.get(name=room_name)
        except cls.DoesNotExist:
            room = cls.objects.create(name=room_name)
            room.participants.add(user1, user2)
        
        return room

class Message(models.Model):
    """Model for chat messages."""
    
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    read_by = models.ManyToManyField(User, related_name='read_messages', blank=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
    
    def mark_as_read(self, user):
        """Mark this message as read by a user."""
        if user != self.sender:
            self.read_by.add(user)
    
    @property
    def is_image_attachment(self):
        """Check if the attachment is an image by examining both name and URL.
        
        Cloudinary strips file extensions from stored names (public_id),
        so we must also check the URL which preserves the extension.
        """
        if not self.attachment:
            return False
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        # Check the stored name
        name_lower = (self.attachment.name or '').lower()
        if any(name_lower.endswith(ext) for ext in image_extensions):
            return True
        # Check the URL (Cloudinary adds the extension back in the URL)
        try:
            url_lower = self.attachment.url.lower()
            # Strip query params before checking extension
            url_path = url_lower.split('?')[0]
            if any(url_path.endswith(ext) for ext in image_extensions):
                return True
        except Exception:
            pass
        return False

    @property
    def is_read(self):
        """Check if all participants have read this message."""
        participants = self.room.participants.all()
        return all(user in self.read_by.all() for user in participants if user != self.sender)
