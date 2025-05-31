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
        <div class="flex justify-between items-center mb-8">
          <h2 class="text-2xl font-bold text-gray-100">Your Documents</h2>
          <router-link
            to="/editor"
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
          </router-link>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          <div
            v-for="doc in documents"
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
                  {{ doc.status }}
                </span>
              </div>

              <p
                class="text-gray-400 text-sm mb-4 line-clamp-2 h-[2.5rem] overflow-hidden"
              >
                {{ doc.content }}
              </p>

              <div class="flex items-center text-xs text-gray-400 gap-2 mt-2">
                <span class="text-cyan-500">{{ doc.type }}</span>
                <span>•</span>
                <span>{{ doc.lastEdited }}</span>
              </div>
            </div>

            <div
              class="p-4 border-t border-gray-700 bg-gray-800/50 min-h-[4rem] flex items-center"
            >
              <div class="flex justify-end gap-3 w-full">
                <!-- Draft actions -->
                <template v-if="doc.status === 'Draft'">
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

                <!-- Pending Review actions -->
                <template v-if="doc.status === 'Pending Review'">
                  <button
                    v-if="isReviewer"
                    @click="reviewDocument(doc.id)"
                    class="text-xs px-3 py-1.5 bg-cyan-700 text-white rounded hover:bg-cyan-600 transition-colors duration-200"
                  >
                    Review
                  </button>
                  <span v-else class="text-xs text-gray-400">
                    Waiting for review...
                  </span>
                </template>

                <!-- Published actions -->
                <template v-if="doc.status === 'Published'">
                  <button
                    @click="viewDocument(doc.id)"
                    class="text-xs px-3 py-1.5 bg-cyan-700 text-white rounded hover:bg-cyan-600 transition-colors duration-200"
                  >
                    View
                  </button>
                  <button
                    @click="createNewVersion(doc.id)"
                    class="text-xs px-3 py-1.5 border border-cyan-700 text-cyan-700 rounded hover:bg-cyan-700 hover:text-white transition-colors duration-200"
                  >
                    New Version
                  </button>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { documentService } from "../services/api";
import { authStore } from "../store/auth";

export default {
  name: "Home",
  setup() {
    const router = useRouter();
    const route = useRoute();
    const documents = ref([]);
    const isLoggedIn = computed(() => authStore.token);
    const isReviewer = ref(true);

    const getStatusClass = (status) => {
      const classes = {
        Draft: "bg-gray-600 text-gray-100",
        "Pending Review": "bg-yellow-600 text-yellow-100",
        Published: "bg-green-600 text-green-100",
        Rejected: "bg-red-600 text-red-100",
      };
      return classes[status] || "bg-gray-600 text-gray-100";
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
      try {
        const reviewerId = "some-reviewer-id"; // Replace with actual reviewer ID logic
        await documentService.submitForReview(docId, reviewerId);
        await fetchDocuments();
      } catch (error) {
        console.error("Error submitting for review:", error);
      }
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

    onMounted(async () => {
      if (isLoggedIn.value) {
        await fetchDocuments();
      }
    });

    return {
      isLoggedIn,
      isReviewer,
      documents,
      getStatusClass,
      submitForReview,
      editDocument,
      reviewDocument,
      viewDocument,
      createNewVersion,
    };
  },
};
</script>
