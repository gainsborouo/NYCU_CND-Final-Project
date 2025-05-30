<template>
  <div class="flex h-[calc(100vh-3.5rem)] bg-gray-950 text-gray-100 font-sans">
    <!-- Not Logged In View -->
    <div v-if="isLoggedIn" class="w-full flex items-center justify-center">
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

        <!-- Documents Grid -->
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

              <p class="text-gray-400 text-sm mb-4 line-clamp-2 h-[2.5rem] overflow-hidden">
                {{ doc.content }}
              </p>

              <div class="flex items-center text-xs text-gray-400 gap-2 mt-2">
                <span class="text-cyan-500">{{ doc.type }}</span>
                <span>•</span>
                <span>{{ doc.lastEdited }}</span>
              </div>
            </div>

            <div class="p-4 border-t border-gray-700 bg-gray-800/50 min-h-[4rem] flex items-center">
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
import { ref, computed } from "vue";
import { authStore } from "../store/auth";

export default {
  name: "Home",
  setup() {
    const isLoggedIn = computed(() => !!authStore.token);
    const isReviewer = ref(true);

    const documents = ref([
      {
        id: 1,
        title: "Test Document",
        content:
          "This is a test document that shows how the layout will look with actual content...",
        lastEdited: "2 days ago",
        type: "Markdown",
        status: "Draft",
      },
      {
        id: 2,
        title: "Pending Review Doc",
        content: "This document is waiting for review...",
        lastEdited: "1 day ago",
        type: "Markdown",
        status: "Pending Review",
      },
      {
        id: 3,
        title: "Published Document",
        content: "This is a published document...",
        lastEdited: "5 days ago",
        type: "Markdown",
        status: "Published",
      },
    ]);

    const getStatusClass = (status) => {
      const classes = {
        Draft: "bg-gray-600 text-white",
        "Pending Review": "bg-yellow-600 text-white",
        Published: "bg-green-600 text-white",
        Rejected: "bg-red-600 text-white",
      };
      return classes[status] || "bg-gray-600 text-white";
    };

    const submitForReview = (docId) => {
      // TODO: Implement submit for review logic
    };

    const editDocument = (docId) => {
      // TODO: Implement edit logic
    };

    const reviewDocument = (docId) => {
      // TODO: Implement review logic
    };

    const viewDocument = (docId) => {
      // TODO: Implement view logic
    };

    const createNewVersion = (docId) => {
      // TODO: Implement new version logic
    };

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
