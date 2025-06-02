<template>
  <div class="min-h-[calc(100vh-3.5rem)] bg-gray-950 text-gray-100 p-6">
    <div class="max-w-3xl mx-auto">
      <div class="flex justify-between items-center mb-8">
        <h2 class="text-2xl font-bold">Notifications</h2>
        <button
          @click="hideRead = !hideRead"
          class="px-3 py-1.5 text-sm border border-gray-600 text-gray-400 rounded hover:bg-gray-700 transition-colors duration-200"
        >
          {{ !hideRead ? "Show all notifications" : "Show unread only" }}
        </button>
      </div>

      <!-- Notifications List -->
      <div class="space-y-4">
        <div
          v-for="notification in filteredNotifications"
          :key="notification.id"
          class="p-4 bg-gray-800 rounded-lg border border-gray-700 hover:bg-gray-800/80 transition-colors duration-200"
        >
          <div class="flex items-start gap-4">
            <div class="flex-grow">
              <p class="font-medium mb-1">{{ notification.title }}</p>
              <p class="text-sm text-gray-400 mb-2">
                {{ notification.message }}
              </p>
              <div class="flex items-center text-xs text-gray-500">
                <span>{{ notification.time }}</span>
              </div>
            </div>
            <div class="flex gap-2">
              <button
                v-if="notification.type === 'document_for_review'"
                @click="goToReview(notification.documentId)"
                class="px-3 py-1.5 text-xs bg-cyan-700 text-white rounded hover:bg-cyan-600 transition-colors duration-200"
              >
                Review
              </button>
              <button
                v-if="
                  notification.type === 'document_approved' ||
                  notification.type === 'document_rejected'
                "
                @click="viewDocument(notification.documentId)"
                class="px-3 py-1.5 text-xs bg-cyan-700 text-white rounded hover:bg-cyan-600 transition-colors duration-200"
              >
                View
              </button>
              <button
                @click="markAsRead(notification.id)"
                class="px-3 py-1.5 text-xs border border-gray-600 text-gray-400 rounded hover:bg-gray-700 transition-colors duration-200"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading and Error States -->
      <!-- <div v-if="loading" class="text-center py-4">
        <span class="loader"></span>
      </div> -->
      <!-- <div v-if="error" class="text-red-500 text-center py-4">
        {{ error }}
      </div> -->
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { notificationService } from "../services/api";

export default {
  name: "Notifications",
  setup() {
    const router = useRouter();
    const notifications = ref([]);
    const loading = ref(false);
    const error = ref(null);
    const hideRead = ref(true);

    const fetchNotifications = async () => {
      try {
        loading.value = true;
        const response = await notificationService.getNotifications();
        notifications.value = response.data.map((notification) => ({
          id: notification.id,
          type: notification.type,
          title: formatNotificationTitle(notification),
          message: notification.message,
          time: formatDate(notification.created_at),
          documentId: notification.document_id,
          isRead: notification.is_read,
        }));
      } catch (err) {
        console.error("Error fetching notifications:", err);
        error.value = "Failed to load notifications";
      } finally {
        loading.value = false;
      }
    };

    const formatNotificationTitle = (notification) => {
      switch (notification.type) {
        case "document_for_review":
          return "Review Request";
        case "document_approved":
          return "Document Approved";
        case "document_rejected":
          return "Document Rejected";
        case "document_state_change":
          return "Document Status Updated";
        case "review_request_cancelled":
          return "Review Request Cancelled";
        default:
          return "Notification";
      }
    };

    const formatDate = (dateString) => {
      const date = new Date(dateString);
      const now = new Date();
      const diff = now - date + date.getTimezoneOffset() * 60000;

      // Convert to minutes
      const minutes = Math.floor(diff / 60000);

      if (minutes < 1) {
        return "just now";
      }

      if (minutes < 60) {
        return `${minutes} minute${minutes > 1 ? "s" : ""} ago`;
      }

      const hours = Math.floor(minutes / 60);
      if (hours < 24) {
        return `${hours} hour${hours > 1 ? "s" : ""} ago`;
      }

      const days = Math.floor(hours / 24);
      if (days < 7) {
        return `${days} day${days > 1 ? "s" : ""} ago`;
      }

      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    };

    const markAsRead = async (notificationId) => {
      try {
        await notificationService.markNotificationStatus(notificationId, true);
        const notification = notifications.value.find(
          (n) => n.id === notificationId
        );
        if (notification) {
          notification.isRead = true;
        }
      } catch (err) {
        console.error("Error marking notification as read:", err);
        error.value = "Failed to update notification";
      }
    };

    const goToReview = (documentId) => {
      router.push(`/review/${documentId}`);
    };

    const viewDocument = (documentId) => {
      router.push(`/viewer/${documentId}`);
    };

    const filteredNotifications = computed(() => {
      if (hideRead.value) {
        return notifications.value.filter((n) => !n.isRead);
      }
      return notifications.value;
    });

    onMounted(() => {
      fetchNotifications();
    });

    return {
      notifications,
      loading,
      error,
      goToReview,
      viewDocument,
      markAsRead,
      hideRead,
      filteredNotifications,
    };
  },
};
</script>

<style>
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from,
.notification-leave-to {
  opacity: 0;
  transform: translateX(30px);
}

.loader {
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-top: 4px solid rgba(255, 255, 255, 0.7);
  border-radius: 50%;
  width: 24px;
  height: 24px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>
