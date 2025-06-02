<template>
  <div class="min-h-[calc(100vh-3.5rem)] bg-gray-950 text-gray-100 font-sans">
    <div class="max-w-4xl mx-auto p-6">
      <!-- Document Header -->
      <div class="flex justify-between items-start mb-8">
        <div>
          <h1 class="text-3xl font-bold mb-2">{{ document.title }}</h1>
          <div class="flex items-center gap-3 text-sm text-gray-400 py-2">
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

      <!-- Document Content -->
      <div class="prose prose-invert max-w-none text-base leading-relaxed">
        <div v-html="renderedContent"></div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from "vue";
import { useRoute } from "vue-router";
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

md.core.ruler.after("block", "add_line_numbers", (state) => {
  let line = 0;
  state.tokens.forEach((token, index) => {
    if (token.map) {
      line = token.map[0];
    }
    if (token.type === "inline" && token.children) {
      token.attrSet("data-line", line);
      token.children.forEach((child) => {
        child.attrSet("data-line", line);
      });
    } else if (token.type.endsWith("_open")) {
      token.attrSet("data-line", line);
    } else if (
      token.type === "text" ||
      token.type === "code_block" ||
      token.type === "fence"
    ) {
      token.attrSet("data-line", line);
    }
  });
});

export default {
  name: "DocumentViewer",
  setup() {
    const route = useRoute();
    const document = ref({
      id: route.params.id,
      title: "",
      description: "",
      type: "Markdown",
      status: "",
      content: "",
      creator_id: null,
      updated_at: null,
    });
    const renderedContent = ref("");
    const authorUsername = ref("");

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

    const fetchDocument = async () => {
      try {
        const documentId = route.params.id;
        const { data } = await documentService.getDocumentDetail(documentId);

        document.value = {
          ...document.value,
          title: data.title || "",
          description: data.description || "",
          status: data.status || "Draft",
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
          renderedContent.value = DOMPurify.sanitize(md.render(content));
        }
      } catch (error) {
        console.error("Error fetching document:", error);
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

    onMounted(() => {
      fetchDocument();
    });

    return {
      document,
      renderedContent,
      getStatusClass,
      mapStatus,
      authorUsername,
      lastModifiedDate: computed(() => formatDate(document.value.updated_at)),
    };
  },
};
</script>

<style scoped></style>
