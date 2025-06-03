<template>
  <div class="min-h-[calc(100vh-3.5rem)] bg-gray-950 text-gray-100">
    <div class="grid grid-cols-2 h-[calc(100vh-3.5rem)]">
      <!-- Document Preview -->
      <div class="border-r border-gray-700 p-6 overflow-y-auto h-full">
        <div class="max-w-2xl mx-auto">
          <h1 class="text-2xl font-bold mb-6">{{ document.title }}</h1>
          <div class="prose prose-invert max-w-none">
            <div v-html="renderedContent"></div>
          </div>
        </div>
      </div>

      <!-- Review Panel -->
      <div class="p-6 bg-gray-800 overflow-y-auto h-full">
        <div class="max-w-2xl mx-auto">
          <!-- Document Header -->
          <div class="flex justify-between items-start mb-8">
            <div>
              <h1 class="text-2xl font-bold mb-2">{{ document.title }}</h1>
              <div class="flex items-center gap-3 text-sm text-gray-400">
                <span class="text-cyan-500">{{ authorUsername }}</span>
                <span>•</span>
                <span>Last updated {{ lastModifiedDate }}</span>
              </div>
            </div>
            <span
              :class="getStatusClass(document.status)"
              class="px-3 py-1 rounded-full text-xs"
            >
              {{ mapStatus(document.status) }}
            </span>
          </div>

          <h2 class="text-xl font-bold mb-6">Review</h2>

          <!-- Review Form -->
          <div class="space-y-6">
            <!-- Decision Buttons -->
            <div>
              <label class="block text-sm font-medium text-gray-300 mb-2">
                Decision
              </label>
              <div class="flex gap-4">
                <button
                  @click="toggleDecision('approve')"
                  :class="[
                    'px-4 py-2 rounded-lg font-medium transition-colors duration-200',
                    decision === 'approve'
                      ? 'bg-green-600 text-white hover:bg-green-500'
                      : 'border border-gray-600 text-gray-400 hover:border-gray-500 hover:text-gray-300',
                  ]"
                >
                  Approve
                </button>
                <button
                  @click="toggleDecision('reject')"
                  :class="[
                    'px-4 py-2 rounded-lg font-medium transition-colors duration-200',
                    decision === 'reject'
                      ? 'bg-red-600 text-white hover:bg-red-500'
                      : 'border border-gray-600 text-gray-400 hover:border-gray-500 hover:text-gray-300',
                  ]"
                >
                  Reject
                </button>
              </div>
            </div>

            <!-- Comments - Only show when reject is selected -->
            <div v-if="decision === 'reject'">
              <label class="block text-sm font-medium text-gray-300 mb-2">
                Rejection Reason <span class="text-red-500">*</span>
              </label>
              <textarea
                v-model="comments"
                rows="4"
                class="w-full px-3 py-2 bg-gray-800 text-gray-100 rounded-lg border border-gray-700 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none"
                placeholder="Please provide a reason for rejection..."
                required
              ></textarea>
            </div>

            <!-- Submit Button -->
            <button
              @click="submitReview"
              :disabled="!isValid"
              class="w-full bg-cyan-700 text-white py-2 rounded-lg hover:bg-cyan-600 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Submit Review
            </button>

            <!-- Error Message -->
            <!-- <div v-if="error" class="text-red-500 text-sm text-center">
              {{ error }}
            </div> -->
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import MarkdownIt from "markdown-it";
import hljs from "highlight.js";
import "highlight.js/styles/github-dark.css";
import DOMPurify from "dompurify";
import { documentService, authService } from "../services/api";

const md = new MarkdownIt({
  html: true,
  highlight: (str, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      try {
        const highlighted = hljs.highlight(str, {
          language: lang,
          ignoreIllegals: true,
        }).value;
        return `<pre class="hljs"><code>${DOMPurify.sanitize(
          highlighted
        )}</code></pre>`;
      } catch (e) {
        return `<pre class="hljs"><code>${DOMPurify.sanitize(
          str
        )}</code></pre>`;
      }
    }
    try {
      const auto = hljs.highlightAuto(str).value;
      return `<pre class="hljs"><code>${DOMPurify.sanitize(auto)}</code></pre>`;
    } catch (e) {
      return `<pre class="hljs"><code>${DOMPurify.sanitize(str)}</code></pre>`;
    }
  },
});

export default {
  name: "DocumentReview",
  setup() {
    const route = useRoute();
    const router = useRouter();
    const document = ref({
      id: route.params.id,
      title: "",
      description: "",
      status: "",
      content: "",
      creator_id: null,
      updated_at: null,
    });
    const authorUsername = ref("");
    const decision = ref("");
    const comments = ref("");
    const error = ref(null);

    const renderedContent = computed(() => {
      return DOMPurify.sanitize(md.render(document.value.content || ""));
    });

    const fetchDocument = async () => {
      try {
        const documentId = route.params.id;
        const { data } = await documentService.getDocumentDetail(documentId);

        document.value = {
          ...document.value,
          title: data.title || "",
          description: data.description || "",
          status: data.status || "",
          creator_id: data.creator_id,
          updated_at: data.updated_at,
        };

        // Fetch author username
        if (data.creator_id) {
          try {
            const username = await authService.getUserUsername(data.creator_id);
            authorUsername.value = username;
          } catch (error) {
            console.error("Error fetching username:", error);
            authorUsername.value = data.creator_id;
          }
        }

        // Fetch markdown content
        if (data.url) {
          const content = await documentService.getMarkdownContent(data.url);
          document.value.content = content;
        }

        // Verify document is in review state
        if (data.status !== "pending_review") {
          router.push("/");
        }
      } catch (error) {
        console.error("Error fetching document:", error);
        error.value = "Failed to load document";
      }
    };

    const isValid = computed(() => {
      if (!decision.value) return false;
      if (decision.value === "reject" && !comments.value.trim()) return false;
      return true;
    });

    const submitReview = async () => {
      if (!isValid.value) return;

      try {
        const reviewData = {
          action: decision.value.toLowerCase(), // ensure lowercase
          rejection_reason: decision.value === "reject" ? comments.value : null, // use null instead of empty string
        };

        await documentService.reviewDocument(
          document.value.id,
          reviewData.action,
          reviewData.rejection_reason
        );

        // Show success message or redirect
        router.push("/");
      } catch (err) {
        console.error("Error submitting review:", err);
        error.value = "Failed to submit review. Please try again.";
      }
    };

    const toggleDecision = (value) => {
      if (decision.value === value) {
        decision.value = "";
      } else {
        decision.value = value;
      }
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
      const classes = {
        draft: "bg-gray-600 text-white",
        pending_review: "bg-yellow-600 text-white",
        published: "bg-green-600 text-white",
        rejected: "bg-red-600 text-white",
      };
      return classes[status?.toLowerCase()] || "bg-gray-600 text-white";
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

      const adjustedDate = new Date(
        date.getTime() - date.getTimezoneOffset() * 60000
      );

      return (
        "on " +
        adjustedDate.toLocaleDateString("en-US", {
          year: "numeric",
          month: "long",
          day: "numeric",
        })
      );
    };

    // Add computed property for formatted date
    const lastModifiedDate = computed(() =>
      formatDate(document.value.updated_at)
    );

    onMounted(() => {
      fetchDocument();
    });

    return {
      document,
      authorUsername,
      decision,
      comments,
      renderedContent,
      submitReview,
      error,
      toggleDecision,
      mapStatus,
      getStatusClass,
      lastModifiedDate,
      isValid,
    };
  },
};
</script>
