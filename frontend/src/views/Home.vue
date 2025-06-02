<template>
  <div class="flex h-[calc(100vh-3.5rem)] bg-gray-950 text-gray-100 font-sans">
    <!-- Not Logged In View -->
    <div v-if="!isLoggedIn" class="w-full flex items-center justify-center">
      <div class="text-center space-y-6">
        <h1 class="text-5xl font-bold text-gray-100">Document Center</h1>
        <p class="text-xl text-gray-400 py-4">
          A collaborative platform for managing and sharing documents
        </p>
        <div class="pt-8">
          <router-link
            to="/login"
            class="px-6 py-3 bg-cyan-700 text-white rounded-lg hover:bg-cyan-600 transition-colors duration-300"
          >
            Get Started
          </router-link>
        </div>
      </div>
    </div>

    <!-- Logged In View -->
    <div v-else class="w-full p-6 overflow-auto">
      <div class="max-w-6xl mx-auto">
        <!-- Add search and filter section -->
        <div class="mb-8 space-y-4 pt-2">
          <!-- Search bar -->
          <div class="relative">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search documents..."
              class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none pl-10"
            />
            <svg
              class="absolute left-3 top-2.5 h-5 w-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>

          <!-- Status filters -->
          <div class="flex flex-wrap gap-2">
            <button
              v-for="status in statusFilters"
              :key="status.value"
              @click="toggleStatusFilter(status.value)"
              :class="[
                'px-3 py-1.5 rounded-2xl text-sm transition-colors duration-200',
                selectedStatuses.includes(status.value)
                  ? status.activeClass
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              ]"
            >
              {{ status.label }}
            </button>
          </div>
        </div>

        <div class="flex justify-between items-center mb-8">
          <h2 class="text-2xl font-bold text-gray-100">Documents</h2>
          <button
            @click="showCreateModal = true"
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
                d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                clip-rule="evenodd"
              />
            </svg>
            New Document
          </button>
        </div>

        <!-- Document grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          <div
            v-for="doc in filteredDocuments"
            :key="doc.id"
            class="flex flex-col bg-gray-800 rounded-lg overflow-hidden border border-gray-700"
          >
            <div class="p-6 flex-grow">
              <div class="flex justify-between items-start mb-4">
                <h3 class="text-lg font-semibold text-gray-100 truncate mr-4">
                  {{ doc.title }}
                </h3>
                <span
                  :class="getStatusClass(doc.status)"
                  class="px-2 py-1 rounded-full text-xs whitespace-nowrap"
                >
                  {{ mapStatus(doc.status) }}
                </span>
              </div>

              <p
                class="text-gray-400 text-sm mb-4 line-clamp-2 h-[2.5rem] overflow-hidden"
              >
                {{ doc.description }}
              </p>

              <div class="flex items-center text-xs text-gray-400 gap-2 mt-2">
                <span class="text-cyan-500">{{
                  usernames[doc.creatorId] || doc.creatorId
                }}</span>
                <span>•</span>
                <span>Last updated {{ formatDate(doc.updatedAt) }}</span>
              </div>
            </div>

            <div
              class="p-4 border-t border-gray-700 bg-gray-800/50 min-h-[4rem] flex items-center"
            >
              <div class="flex justify-end gap-3 w-full">
                <!-- Draft actions -->
                <template v-if="doc.status === 'draft'">
                  <button
                    @click="editDocument(doc.id)"
                    class="text-xs px-3 py-1.5 border border-cyan-700 text-cyan-700 rounded hover:bg-cyan-700 hover:text-white transition-colors duration-200"
                  >
                    Edit
                  </button>
                  <button
                    @click="submitForReview(doc.id)"
                    class="text-xs px-3 py-1.5 bg-cyan-700 text-white rounded hover:bg-cyan-600 transition-colors duration-200"
                  >
                    Submit for Review
                  </button>
                </template>

                <template v-if="doc.status === 'rejected'">
                  <button
                    @click="editDocument(doc.id)"
                    class="text-xs px-3 py-1.5 border border-cyan-700 text-cyan-700 rounded hover:bg-cyan-700 hover:text-white transition-colors duration-200"
                  >
                    Edit
                  </button>
                  <button
                    @click="submitForReview(doc.id)"
                    class="text-xs px-3 py-1.5 bg-cyan-700 text-white rounded hover:bg-cyan-600 transition-colors duration-200"
                  >
                    Submit for Review
                  </button>
                  <button
                    @click="viewDocument(doc.id)"
                    class="text-xs px-3 py-1.5 border border-cyan-700 text-cyan-700 rounded hover:bg-cyan-700 hover:text-white transition-colors duration-200"
                  >
                    View
                  </button>
                </template>

                <!-- Pending Review actions -->
                <template v-if="doc.status === 'pending_review'">
                  <button
                    @click="viewDocument(doc.id)"
                    class="text-xs px-3 py-1.5 border border-cyan-700 text-cyan-700 rounded hover:bg-cyan-700 hover:text-white transition-colors duration-200"
                  >
                    View
                  </button>
                  <button
                    v-if="doc.currentReviewerId === getCurrentUserId()"
                    @click="reviewDocument(doc.id)"
                    class="text-xs px-3 py-1.5 bg-cyan-700 text-white rounded hover:bg-cyan-600 transition-colors duration-200"
                  >
                    Review
                  </button>
                  <!-- <span v-else-if="doc.creatorId === getCurrentUserId()" class="text-xs text-gray-400">
                    Waiting for review...
                  </span> -->
                </template>

                <!-- Published actions -->
                <template v-if="doc.status === 'published'">
                  <button
                    @click="viewDocument(doc.id)"
                    class="text-xs px-3 py-1.5 border border-cyan-700 text-cyan-700 rounded hover:bg-cyan-700 hover:text-white transition-colors duration-200"
                  >
                    View
                  </button>
                  <!-- <button
                    @click="createNewVersion(doc.id)"
                    class="text-xs px-3 py-1.5 border border-cyan-700 text-cyan-700 rounded hover:bg-cyan-700 hover:text-white transition-colors duration-200"
                  >
                    New Version
                  </button> -->
                </template>
              </div>
            </div>
          </div>
        </div>

        <!-- Create Document Modal -->
        <Transition
          enter-active-class="transition duration-300 ease-out"
          enter-from-class="transform opacity-0"
          enter-to-class="transform opacity-100"
          leave-active-class="transition duration-200 ease-in"
          leave-from-class="transform opacity-100"
          leave-to-class="transform opacity-0"
        >
          <div
            v-if="showCreateModal"
            class="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div
              class="fixed inset-0 bg-gray-950/90 backdrop-blur-sm"
              @click="showCreateModal = false"
            ></div>
            <div
              class="bg-gray-800 rounded-lg p-6 w-full max-w-md relative z-10"
            >
              <h3 class="text-xl font-semibold mb-4">Create New Document</h3>
              <form @submit.prevent="createDocument">
                <div class="mb-4">
                  <label class="block text-sm font-medium mb-2">Title</label>
                  <input
                    v-model="newDocument.title"
                    type="text"
                    class="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                    required
                  />
                </div>
                <div class="mb-4">
                  <label class="block text-sm font-medium mb-2"
                    >Description</label
                  >
                  <textarea
                    v-model="newDocument.description"
                    class="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                    rows="3"
                  ></textarea>
                </div>
                <div class="mb-6">
                  <label class="block text-sm font-medium mb-2">Group</label>
                  <select
                    v-model="newDocument.realmId"
                    class="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                    required
                  >
                    <option value="" disabled>Select a group</option>
                    <option
                      v-for="group in userGroups"
                      :key="group.id"
                      :value="group.id"
                    >
                      {{ group.name }}
                    </option>
                  </select>
                </div>
                <div class="flex justify-end gap-3">
                  <button
                    type="button"
                    @click="showCreateModal = false"
                    class="px-4 py-2 text-gray-300 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    class="px-4 py-2 bg-cyan-700 text-white rounded-lg hover:bg-cyan-600"
                  >
                    Create
                  </button>
                </div>
              </form>
            </div>
          </div>
        </Transition>

        <SubmitForReviewModal
          :show="showSubmitModal"
          :document-id="selectedDocumentId"
          :group-id="selectedGroupId"
          @close="showSubmitModal = false"
          @submitted="handleReviewSubmitted"
        />
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import {
  documentService,
  authService,
  notificationService,
} from "../services/api";
import { authStore } from "../store/auth";
import SubmitForReviewModal from "../components/SubmitForReviewModal.vue";

export default {
  name: "Home",
  components: {
    SubmitForReviewModal,
  },
  setup() {
    const router = useRouter();
    const route = useRoute();
    const documents = ref([]);
    const isLoggedIn = computed(() => authStore.token);
    const isReviewer = ref(true);
    const showCreateModal = ref(false);
    const showSubmitModal = ref(false);
    const selectedDocumentId = ref(null);
    const selectedGroupId = ref(null);
    const userGroups = ref([]);
    const newDocument = ref({
      title: "",
      description: "",
      realmId: "",
    });
    const groupNames = ref({});
    const usernames = ref({});
    const searchQuery = ref('');
    const selectedStatuses = ref([]);

    const statusFilters = [
      { label: 'All', value: '', activeClass: 'bg-cyan-700 text-white' },
      { label: 'Draft', value: 'draft', activeClass: 'bg-gray-600 text-white' },
      { label: 'Pending Review', value: 'pending_review', activeClass: 'bg-yellow-600 text-white' },
      { label: 'Published', value: 'published', activeClass: 'bg-green-600 text-white' },
      { label: 'Rejected', value: 'rejected', activeClass: 'bg-red-600 text-white' },
    ];

    const toggleStatusFilter = (status) => {
      if (status === '') {
        // If "All" is clicked, clear other filters
        selectedStatuses.value = [];
        return;
      }
      
      const index = selectedStatuses.value.indexOf(status);
      if (index === -1) {
        selectedStatuses.value.push(status);
      } else {
        selectedStatuses.value.splice(index, 1);
      }
    };

    const filteredDocuments = computed(() => {
      return documents.value
        .filter(doc => {
          // Apply search filter
          const searchLower = searchQuery.value.toLowerCase();
          const matchesSearch = 
            doc.title.toLowerCase().includes(searchLower) ||
            doc.description.toLowerCase().includes(searchLower);

          // Apply status filter
          const matchesStatus = 
            selectedStatuses.value.length === 0 || 
            selectedStatuses.value.includes(doc.status);

          return matchesSearch && matchesStatus;
        })
        .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt)); // Sort by latest update
    });

    const fetchGroupNames = async () => {
      try {
        const response = await authService.getGroupNames();
        groupNames.value = response.data;
      } catch (error) {
        console.error("Error fetching group names:", error);
      }
    };

    const fetchUsername = async (userId) => {
      if (!usernames.value[userId]) {
        try {
          const username = await authService.getUserUsername(userId);
          usernames.value[userId] = username;
        } catch (error) {
          console.error(`Error fetching username for ${userId}:`, error);
          usernames.value[userId] = userId;
        }
      }
      return usernames.value[userId];
    };

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
      const mappedStatus = mapStatus(status);
      const classes = {
        Draft: "bg-gray-600 text-gray-100",
        "Pending Review": "bg-yellow-600 text-yellow-100",
        Published: "bg-green-600 text-green-100",
        Rejected: "bg-red-600 text-red-100",
      };
      return classes[mappedStatus] || "bg-gray-600 text-gray-100";
    };

    const fetchDocuments = async () => {
      try {
        const response = await documentService.getAllDocuments();
        documents.value = response.data;
      } catch (error) {
        console.error("Error fetching documents:", error);
      }
    };

    const submitForReview = async (docId) => {
      const doc = documents.value.find((d) => d.id === docId);
      if (!doc) return;

      selectedDocumentId.value = docId;
      selectedGroupId.value = doc.realmId;
      showSubmitModal.value = true;
    };

    const editDocument = (docId) => {
      if (!docId) {
        console.error("No document ID provided");
        return;
      }
      router.push(`/editor/${docId}`);
    };

    const reviewDocument = (docId) => {
      if (!docId) {
        console.error("No document ID provided");
        return;
      }
      router.push(`/review/${docId}`);
    };

    const viewDocument = (docId) => {
      if (!docId) {
        console.error("No document ID provided");
        return;
      }
      router.push(`/viewer/${docId}`);
    };

    const createNewVersion = async (docId) => {
      if (!docId) {
        console.error("No document ID provided");
        return;
      }
      try {
        const response = await documentService.createDocument({
          originalId: docId,
          type: "new_version",
        });
        router.push(`/editor/${response.data.id}`);
      } catch (error) {
        console.error("Error creating new version:", error);
      }
    };

    const createDocument = async () => {
      try {
        const response = await documentService.createDocument({
          title: newDocument.value.title,
          description: newDocument.value.description,
          realmId: newDocument.value.realmId,
        });

        showCreateModal.value = false;
        if (response.data && response.data.id) {
          router.push(`/editor/${response.data.id}`);
          // Reset form
          newDocument.value = {
            title: "",
            description: "",
            realmId: "",
          };
        }
      } catch (error) {
        console.error("Error creating document:", error);
        // You might want to show an error message to the user here
      }
    };

    const handleReviewSubmitted = async () => {
      await fetchDocuments();
      // Optional: Show success message
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

      return (
        "on " +
        date.toLocaleDateString("en-US", {
          year: "numeric",
          month: "long",
          day: "numeric",
        })
      );
    };

    // Update onMounted to fetch group names
    onMounted(async () => {
      if (isLoggedIn.value) {
        await Promise.all([fetchGroupNames(), fetchDocuments()]);
        userGroups.value = getUserGroups();
        for (const doc of documents.value) {
          await fetchUsername(doc.creatorId);
        }
      }
    });

    const getUserGroups = () => {
      try {
        const token = authStore.token;
        if (!token) return [];

        const payload = JSON.parse(atob(token.split(".")[1]));
        const realmRoles = payload.realm_roles || {};

        return Object.entries(realmRoles).map(([id, roles]) => ({
          id,
          name: groupNames.value[id] || `Group ${id}`,
          roles,
        }));
      } catch (error) {
        console.error("Error parsing user groups:", error);
        return [];
      }
    };

    const getCurrentUserId = () => {
      try {
        const token = authStore.token;
        if (!token) return null;
        const payload = JSON.parse(atob(token.split(".")[1]));
        return payload.uid;
      } catch (error) {
        console.error("Error getting current user ID:", error);
        return null;
      }
    };

    return {
      isLoggedIn,
      isReviewer,
      documents,
      usernames,
      getStatusClass,
      mapStatus,
      submitForReview,
      editDocument,
      reviewDocument,
      viewDocument,
      createNewVersion,
      showCreateModal,
      newDocument,
      createDocument,
      userGroups,
      formatDate,
      groupNames,
      fetchUsername,
      showSubmitModal,
      selectedDocumentId,
      selectedGroupId,
      handleReviewSubmitted,
      getCurrentUserId,
      searchQuery,
      statusFilters,
      filteredDocuments,
      toggleStatusFilter,
      selectedStatuses,
    };
  },
};
</script>
