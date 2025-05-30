<template>
  <div class="min-h-[calc(100vh-3.5rem)] bg-gray-950 text-gray-100 p-6">
    <div class="max-w-3xl mx-auto">
      <h2 class="text-2xl font-bold mb-8">Notifications</h2>

      <!-- Notifications List -->
      <div class="space-y-4">
        <div
          v-for="notification in notifications"
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
                v-if="notification.type === 'review_request'"
                @click="goToReview(notification.documentId)"
                class="px-3 py-1.5 text-xs bg-cyan-700 text-white rounded hover:bg-cyan-600 transition-colors duration-200"
              >
                Review
              </button>
              <button
                v-if="notification.type === 'review_complete'"
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
    </div>
  </div>
</template>

<script>
import { ref } from "vue";
import { useRouter } from "vue-router";

export default {
  name: "Notifications",
  setup() {
    const router = useRouter();

    const notifications = ref([
      {
        id: 1,
        type: "review_request",
        title: "Review Request: Safety Guidelines Update",
        message: "John Doe has submitted a document for your review.",
        time: "10 minutes ago",
        documentId: 123,
        isRead: false,
      },
      {
        id: 2,
        type: "review_complete",
        title: "Document Approved: Manufacturing Process",
        message: "Your document has been approved by Jane Smith.",
        time: "2 hours ago",
        documentId: 456,
        isRead: false,
      },
      {
        id: 3,
        type: "review_request",
        title: "Review Request: Equipment Manual",
        message:
          "Alex Johnson needs your review on updated equipment procedures.",
        time: "1 day ago",
        documentId: 789,
        isRead: false,
      },
      {
        id: 4,
        type: "review_complete",
        title: "Document Rejected: Training Guide",
        message:
          "Your document was rejected. Please check the comments and revise.",
        time: "2 days ago",
        documentId: 101,
        isRead: true,
      },
    ]);

    const goToReview = (documentId) => {
      router.push(`/review/${documentId}`);
    };

    const viewDocument = (documentId) => {
      router.push(`/viewer/${documentId}`);
    };

    const markAsRead = (notificationId) => {
      const notification = notifications.value.find(
        (n) => n.id === notificationId
      );
      if (notification) {
        notification.isRead = true;
        // TODO: Update backend when implemented
        console.log("Marked as read:", notificationId);
      }
    };

    return {
      notifications,
      goToReview,
      viewDocument,
      markAsRead,
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
</style>
