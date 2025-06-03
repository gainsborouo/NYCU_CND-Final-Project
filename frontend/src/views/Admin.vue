<template>
  <div class="flex h-[calc(100vh-3.5rem)] bg-gray-950 text-gray-100 font-sans">
    <div class="w-full p-6 overflow-auto">
      <div class="max-w-6xl mx-auto">
        <!-- Header section -->
        <div class="flex justify-between items-center mb-8">
          <h2 class="text-2xl font-bold text-gray-100">Document Admin</h2>
          <button
            @click="goBack"
            class="px-4 py-2 bg-cyan-700 text-white rounded-lg hover:bg-cyan-600 transition-colors duration-300 flex items-center gap-2"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"
                clip-rule="evenodd"
              />
            </svg>
            Back
          </button>
        </div>

        <!-- Loading state -->
        <div v-if="isLoading" class="flex justify-center py-10">
          <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-500"></div>
        </div>

        <div v-else-if="error" class="bg-red-900 text-white p-4 rounded-lg mb-6">
          {{ error }}
        </div>

        <div v-else>
          <!-- Document info header -->
          <div class="bg-gray-800 rounded-lg p-5 mb-6 border border-gray-700">
            <h3 class="text-xl font-bold mb-2">{{ document.title }}</h3>
            <p class="text-gray-400 mb-3">{{ document.description }}</p>
            <div class="flex items-center gap-4 text-sm">
              <div class="flex items-center gap-2">
                <span class="text-gray-400">Status:</span>
                <span :class="getStatusClass(document.status)" class="px-2 py-1 rounded-full text-xs">
                  {{ mapStatus(document.status) }}
                </span>
              </div>
              <!-- For document creator in header -->
              <div>
                <span class="text-gray-400">Created by:</span>
                <span class="text-cyan-400 ml-1">{{ usernames[document.creatorId] || document.creatorId }}</span>
              </div>

              <!-- For current reviewer in header -->
              <div v-if="document.currentReviewerId">
                <span class="text-gray-400">Current reviewer:</span>
                <span class="text-cyan-400 ml-1">{{ usernames[document.currentReviewerId] || document.currentReviewerId }}</span>
              </div>
            </div>
          </div>

          <!-- Two-column layout for History and Update panels -->
          <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <!-- Document History Timeline - Left column (5/12 width) -->
            <div class="lg:col-span-5 flex flex-col" style="min-height: calc(50vh)">
              <h3 class="text-lg font-bold mb-4 text-gray-200">Document History</h3>
              <div class="bg-gray-800 rounded-lg p-6 border border-gray-700 relative flex-1 flex flex-col">
                <!-- Timeline visualization with scrolling -->
                <div v-if="documentHistory.length === 0" class="text-gray-400 text-center py-8">
                  No history found for this document.
                </div>
                
                <!-- Timeline with nodes and scrolling -->
                <div v-else class="relative flex-1 overflow-y-auto pr-2" style="max-height: calc(50vh)">
                  <!-- Timeline container with relative positioning -->
                  <div class="relative min-h-full">
                    <!-- Timeline vertical line that extends based on content -->
                    <div class="absolute left-2 w-0.5 bg-gray-700" 
                         :style="{
                           top: '0',
                           height: documentHistory.length ? 'calc(100% - 16px)' : '100%'
                         }">
                    </div>
                    
                    <!-- Timeline items -->
                    <div v-for="(historyItem, index) in documentHistory" :key="historyItem.id" class="relative pl-10 pb-8">
                      <!-- Timeline node -->
                      <div :class="getActionNodeClass(historyItem.action)" class="absolute left-2 w-6 h-6 rounded-full flex items-center justify-center transform -translate-x-1/2 border-4 border-gray-800 z-10"></div>
                      
                      <!-- Timeline content -->
                      <div class="bg-gray-700 rounded-lg p-4">
                        <!-- Content remains the same -->
                        <div class="flex justify-between items-start">
                          <div>
                            <span :class="getActionBadgeClass(historyItem.action)" class="px-2 py-1 rounded-full text-xs inline-block mb-2">
                              {{ formatAction(historyItem.action) }}
                            </span>
                          </div>
                          <div class="text-xs text-gray-400">
                            {{ formatDateTime(historyItem.reviewed_at) }}
                          </div>
                        </div>
                        
                        <div class="text-sm mb-2">
                          <span class="font-semibold text-cyan-400">{{ usernames[historyItem.reviewer_id] || historyItem.reviewer_id }}</span>
                          <span class="text-gray-300"> {{ getActionDescription(historyItem.action) }}</span>
                        </div>
                        
                        <!-- Status change info -->
                        <div v-if="historyItem.new_document_status" class="text-xs text-gray-400 mt-2">
                          Status changed to 
                          <span :class="getStatusBadgeClass(historyItem.new_document_status)" class="px-1 py-0.5 rounded text-xs">
                            {{ mapStatus(historyItem.new_document_status) }}
                          </span>
                        </div>
                        
                        <!-- Rejection reason if applicable -->
                        <div v-if="historyItem.rejection_reason && historyItem.rejection_reason !== '0'" class="mt-3 p-3 bg-gray-800 rounded text-sm text-red-300 border-l-2 border-red-500">
                          "{{ historyItem.rejection_reason }}"
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Document Update Panel - Right column (7/12 width) -->
            <div class="lg:col-span-7 flex flex-col" style="min-height: 500px">
              <h3 class="text-lg font-bold mb-4 text-gray-200">Update Document</h3>
              <div class="bg-gray-800 rounded-lg p-6 border border-gray-700 flex-1">
                <form @submit.prevent="updateDocument">
                  <div class="space-y-6">
                    <!-- Title field -->
                    <div>
                      <label for="title" class="block text-sm font-medium text-gray-300 mb-1">Title</label>
                      <input
                        id="title"
                        v-model="updatedDocument.title"
                        type="text"
                        class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                      />
                    </div>
                    
                    <!-- Description field -->
                    <div>
                      <label for="description" class="block text-sm font-medium text-gray-300 mb-1">Description</label>
                      <textarea
                        id="description"
                        v-model="updatedDocument.description"
                        rows="3"
                        class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                      ></textarea>
                    </div>
                    
                    <!-- Status dropdown -->
                    <div>
                      <label for="status" class="block text-sm font-medium text-gray-300 mb-1">Status</label>
                      <select
                        id="status"
                        v-model="updatedDocument.status"
                        @change="handleStatusChange"
                        class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                      >
                        <option value="draft">Draft</option>
                        <option value="pending_review">Pending Review</option>
                        <option value="published">Published</option>
                        <option value="rejected">Rejected</option>
                      </select>
                    </div>
                    
                    <!-- Current Reviewer dropdown -->
                    <div v-if="updatedDocument.status === 'pending_review'">
                      <div v-if="reviewers.length > 0">
                        <label for="reviewer" class="block text-sm font-medium text-gray-300 mb-1">
                          Current Reviewer <span class="text-red-500">*</span>
                        </label>
                        <select
                          id="reviewer"
                          v-model="updatedDocument.currentReviewerId"
                          :class="[
                            'w-full px-4 py-2 bg-gray-700 border rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none',
                            reviewerError ? 'border-red-500' : 'border-gray-600'
                          ]"
                          required
                        >
                          <option value="" disabled>Select a reviewer</option>
                          <option v-for="reviewer in reviewers" :key="reviewer.id" :value="reviewer.id">
                            {{ reviewer.username || reviewer.id }}
                          </option>
                        </select>
                        <p v-if="reviewerError" class="mt-1 text-sm text-red-500">
                          {{ reviewerError }}
                        </p>
                      </div>
                      <!-- Display when no reviewers are available -->
                      <div v-else class="mt-3 p-4 bg-yellow-900/30 border border-yellow-700 rounded-lg">
                        <p class="text-yellow-300 text-sm flex items-center">
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                          </svg>
                          No reviewers available for this realm. Please add reviewers to be able to assign them.
                        </p>
                      </div>
                    </div>
                    
                    <!-- Buttons -->
                    <div class="flex justify-end gap-3 mt-6">
                      <button
                        type="button"
                        @click="resetForm"
                        class="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                      >
                        Reset
                      </button>
                      <button
                        type="submit"
                        :disabled="isUpdating"
                        class="px-4 py-2 bg-cyan-700 text-white rounded-lg hover:bg-cyan-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                      >
                        <svg v-if="isUpdating" class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span>{{ isUpdating ? 'Updating...' : 'Update Document' }}</span>
                      </button>
                    </div>
                    
                    <!-- Success/Error message -->
                    <div v-if="updateMessage" :class="updateSuccess ? 'bg-green-900 text-green-100' : 'bg-red-900 text-red-100'" class="p-3 rounded-lg text-sm mt-4">
                      {{ updateMessage }}
                    </div>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, reactive, computed, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { documentService, authService } from "../services/api";

export default {
  name: "Admin",
  props: {
    id: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const router = useRouter();
    const route = useRoute();
    const searchQuery = ref("");
    const isLoading = ref(true);
    const error = ref(null);
    
    // Document data
    const document = ref({});
    const documentHistory = ref([]);
    const updatedDocument = ref({
      title: "",
      description: "",
      status: "",
      currentReviewerId: ""
    });
    
    // Reviewers data
    const reviewers = ref([]);
    const isLoadingReviewers = ref(false);
    
    // Update status
    const isUpdating = ref(false);
    const updateMessage = ref("");
    const updateSuccess = ref(false);
    
    // Usernames mapping
    const usernames = ref({});
    
    // Navigation function
    const goBack = () => {
      router.back();
    };
    
    // Format functions
    const mapStatus = (status) => {
      const statusMap = {
        draft: "Draft",
        pending_review: "Pending Review",
        published: "Published",
        rejected: "Rejected",
      };
      return statusMap[status?.toLowerCase()] || status;
    };
    
    const getStatusClass = (status) => {
      const statusClasses = {
        draft: "bg-gray-600 text-gray-100",
        pending_review: "bg-yellow-600 text-yellow-100",
        published: "bg-green-600 text-green-100",
        rejected: "bg-red-600 text-red-100",
      };
      return statusClasses[status?.toLowerCase()] || "bg-gray-600 text-gray-100";
    };
    
    const getStatusBadgeClass = (status) => {
      const statusClasses = {
        draft: "bg-gray-700 text-gray-100",
        pending_review: "bg-yellow-700 text-yellow-100",
        published: "bg-green-700 text-green-100",
        rejected: "bg-red-700 text-red-100",
      };
      return statusClasses[status?.toLowerCase()] || "bg-gray-700 text-gray-100";
    };
    
    const formatAction = (action) => {
      const actionMap = {
        'approve': 'Approved',
        'reject': 'Rejected',
        'submit': 'Submitted for Review',
        'create': 'Created',
        'update': 'Updated'
      };
      return actionMap[action?.toLowerCase()] || action;
    };
    
    const getActionNodeClass = (action) => {
      const actionClasses = {
        'approve': 'bg-green-500',
        'reject': 'bg-red-500',
        'submit': 'bg-yellow-500',
        'create': 'bg-cyan-500',
        'update': 'bg-blue-500'
      };
      return actionClasses[action?.toLowerCase()] || 'bg-gray-500';
    };
    
    const getActionBadgeClass = (action) => {
      const actionClasses = {
        'approve': 'bg-green-700 text-green-100',
        'reject': 'bg-red-700 text-red-100',
        'submit': 'bg-yellow-700 text-yellow-100',
        'create': 'bg-cyan-700 text-cyan-100',
        'update': 'bg-blue-700 text-blue-100'
      };
      return actionClasses[action?.toLowerCase()] || 'bg-gray-700 text-gray-100';
    };
    
    const getActionDescription = (action) => {
      const actionDescriptions = {
        'approve': ' approved the document',
        'reject': ' rejected the document',
        'submit': ' submitted the document for review',
        'create': ' created the document',
        'update': ' updated the document'
      };
      return actionDescriptions[action?.toLowerCase()] || action;
    };
    
    const formatDateTime = (dateTimeString) => {
      if (!dateTimeString) return "";
      const date = new Date(dateTimeString);
      
      // Check if date is valid
      if (isNaN(date.getTime())) {
        return dateTimeString;
      }
      
      return date.toLocaleString();
    };
    
    // Fetch document details
    const fetchDocumentDetails = async () => {
      isLoading.value = true;
      error.value = null;
      
      try {
        const response = await documentService.getDocumentDetail(props.id);
        document.value = {
          id: response.data.id,
          title: response.data.title,
          description: response.data.description,
          status: response.data.status,
          creatorId: response.data.creator_id,
          realmId: response.data.realm_id,
          currentReviewerId: response.data.current_reviewer_id,
          publishedAt: response.data.published_at,
          createdAt: response.data.created_at,
          updatedAt: response.data.updated_at,
          url: response.data.url,
        };
        
        // Initialize form with current values
        updatedDocument.value = {
          title: document.value.title,
          description: document.value.description,
          status: document.value.status,
          currentReviewerId: document.value.currentReviewerId || ""
        };
        
        // Fetch reviewers for the document's realm
        if (document.value.realmId) {
          fetchReviewers(document.value.realmId);
        }
        
      } catch (err) {
        console.error("Error fetching document:", err);
        error.value = "Failed to load document details. Please try again.";
      }
    };
    
    // Fetch document history
    const fetchDocumentHistory = async () => {
      try {
        const response = await documentService.getDocumentReviewHistory(props.id);
        // Response data is already in the correct format, no transformation needed
        documentHistory.value = response.data;
        
        // Fetch usernames for reviewers
        await fetchUsernames();
      } catch (err) {
        console.error("Error fetching document history:", err);
      } finally {
        isLoading.value = false;
      }
    };
    
    // Fetch reviewers for the realm
    const fetchReviewers = async (realmId) => {
      isLoadingReviewers.value = true;
      try {
        const response = await authService.getGroupReviewers(realmId);
        
        // Transform the object into an array of objects
        const reviewersArray = Object.entries(response).map(([id, username]) => ({
          id,
          username
        }));
        
        reviewers.value = reviewersArray;
        
        console.log("Original response:", response);
        console.log("Transformed reviewers:", reviewers.value);
        
        // Call handleStatusChange after reviewers are loaded
        handleStatusChange();
      } catch (err) {
        console.error("Error fetching reviewers:", err);
        reviewers.value = []; // Ensure it's an empty array on error
      } finally {
        isLoadingReviewers.value = false;
      }
    };
    
    // Fetch usernames for the reviewers and document creator/reviewer
    const fetchUsernames = async () => {
      // Add document creator to the usernames to fetch
      const userIdsToFetch = new Set();
      
      // Add document creator if available
      if (document.value.creatorId) {
        userIdsToFetch.add(document.value.creatorId);
      }
      
      // Add current reviewer if available
      if (document.value.currentReviewerId) {
        userIdsToFetch.add(document.value.currentReviewerId);
      }
      
      // Add all reviewers from history
      documentHistory.value.forEach(item => {
        if (item.reviewer_id) {
          userIdsToFetch.add(item.reviewer_id);
        }
      });
      
      // Fetch usernames for all unique user IDs
      for (const userId of userIdsToFetch) {
        if (!usernames.value[userId]) {
          try {
            const username = await authService.getUserUsername(userId);
            usernames.value[userId] = username;
          } catch (err) {
            console.error(`Error fetching username for ID ${userId}:`, err);
          }
        }
      }
    };
    
    // Update document
    const updateDocument = async () => {
      isUpdating.value = true;
      updateMessage.value = "";
      reviewerError.value = "";
      
      // Validate reviewer selection when changing status to pending_review
      if (updatedDocument.value.status === 'pending_review' && !updatedDocument.value.currentReviewerId) {
        reviewerError.value = "A reviewer is required when setting status to Pending Review";
        isUpdating.value = false;
        return;
      }
      
      try {
        // Convert field names to match API expectations
        const updateData = {
          title: updatedDocument.value.title,
          description: updatedDocument.value.description,
          status: updatedDocument.value.status,
          current_reviewer_id: updatedDocument.value.currentReviewerId || null
        };
        
        await documentService.updateDocumentFields(props.id, updateData);
        
        // Show success message
        updateSuccess.value = true;
        updateMessage.value = "Document updated successfully!";
        
        // Refresh document data
        await fetchDocumentDetails();
        await fetchDocumentHistory();
      } catch (err) {
        console.error("Error updating document:", err);
        updateSuccess.value = false;
        updateMessage.value = "Failed to update document. Please try again.";
      } finally {
        isUpdating.value = false;
      }
    };
    
    // Reset form to original values
    const resetForm = () => {
      updatedDocument.value = {
        title: document.value.title,
        description: document.value.description,
        status: document.value.status,
        currentReviewerId: document.value.currentReviewerId || ""
      };
      updateMessage.value = "";
    };
    
    // Status change handling
    const reviewerError = ref("");
    const showReviewerSelection = ref(false);
    
    const handleStatusChange = () => {
      if (updatedDocument.value.status === 'pending_review') {
        showReviewerSelection.value = true;
        if (!updatedDocument.value.currentReviewerId) {
          reviewerError.value = "A reviewer is required when setting status to Pending Review";
        } else {
          reviewerError.value = "";
        }
      } else {
        showReviewerSelection.value = false;
        reviewerError.value = "";
      }
    };
    
    // Replace the current watcher with this
    watch(
      () => updatedDocument.value.status,
      (newStatus) => {
        console.log("Status changed to:", newStatus); // Debug log
        handleStatusChange();
      },
      { immediate: true } // This is key - it will run the watcher immediately on setup
    );
    
    // Initialize the showReviewerSelection based on initial status
    onMounted(async () => {
      console.log("Admin panel mounted for document ID:", props.id);
      await fetchDocumentDetails();
      await fetchDocumentHistory();
      await fetchUsernames();
    });
    
    return {
      searchQuery,
      isLoading,
      error,
      document,
      documentHistory,
      updatedDocument,
      reviewers,
      isLoadingReviewers,
      isUpdating,
      updateMessage,
      updateSuccess,
      goBack,
      mapStatus,
      getStatusClass,
      getStatusBadgeClass,
      formatAction,
      getActionNodeClass,
      getActionBadgeClass,
      getActionDescription,
      formatDateTime,
      updateDocument,
      resetForm,
      usernames,
      reviewerError,
      showReviewerSelection,
      handleStatusChange
    };
  }
};
</script>

<style>
/* Inherit styles from the Home component */
.staggered-fade-enter-active,
.staggered-fade-leave-active {
  transition: opacity 0.5s, transform 0.5s;
}

.staggered-fade-enter,
.staggered-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.staggered-fade-move {
  transition: transform 0.5s ease;
  position: relative;
  z-index: 1;
}

.staggered-fade-leave-active {
  position: absolute;
  opacity: 0;
  z-index: 0;
}
</style>