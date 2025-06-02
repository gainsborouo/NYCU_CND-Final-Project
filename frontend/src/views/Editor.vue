<template>
  <div
    class="h-[calc(100vh-3.5rem)] bg-gray-900 text-gray-100 font-sans relative flex flex-col"
  >
    <!-- Document Header -->
    <div class="border-b border-gray-700 bg-gray-800 p-4">
      <div class="max-w-4xl mx-auto">
        <div class="flex justify-between items-center">
          <h1
            class="text-2xl font-bold cursor-pointer"
            @click="showEditModal = true"
          >
            {{ documentTitle || "Untitled Document" }}
          </h1>
          <div class="flex items-center gap-3 text-sm text-gray-400">
            <span class="text-cyan-500">{{ authorUsername }}</span>
            <span>•</span>
            <span>Last modified: {{ lastModifiedDate }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Modal -->
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="transform opacity-0"
      enter-to-class="transform opacity-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="transform opacity-100"
      leave-to-class="transform opacity-0"
    >
      <div
        v-if="showEditModal"
        class="fixed inset-0 bg-gray-950/90 flex items-center justify-center p-4 z-50"
      >
        <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md">
          <h3 class="text-xl font-semibold mb-4">Edit Document Details</h3>
          <form @submit.prevent="saveMetadata">
            <div class="mb-4">
              <label class="block text-sm font-medium mb-2">Title</label>
              <input
                v-model="editingTitle"
                type="text"
                class="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                required
              />
            </div>
            <div class="mb-6">
              <label class="block text-sm font-medium mb-2">Description</label>
              <textarea
                v-model="editingDescription"
                class="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                rows="3"
              ></textarea>
            </div>
            <div class="flex justify-end gap-3">
              <button
                type="button"
                @click="showEditModal = false"
                class="px-4 py-2 text-gray-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="px-4 py-2 bg-cyan-700 text-white rounded-lg hover:bg-cyan-600"
              >
                Save
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>

    <!-- Editor Container -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Markdown Editor -->
      <div
        class="w-1/2 border-r border-gray-700 flex bg-gray-800"
        @drop.prevent="handleDrop"
        @dragover.prevent
      >
        <div class="flex-1 p-6">
          <textarea
            v-model="markdown"
            ref="textareaRef"
            @click="updateCursor"
            @keyup="updateCursor"
            @scroll="handleScroll"
            @input="updateCursor"
            @mouseup="updateCursor"
            class="w-full h-full p-4 font-mono text-sm border border-gray-700 rounded-lg resize-none focus:outline-none bg-gray-900 text-gray-100"
            placeholder="Write your markdown here..."
          ></textarea>
        </div>
      </div>

      <!-- Rendered Output -->
      <div class="w-1/2 p-6 overflow-auto bg-gray-950" ref="previewRef">
        <div class="prose prose-invert max-w-none text-base leading-relaxed">
          <div v-html="renderedMarkdown"></div>
        </div>
      </div>

      <!-- Floating Save Button -->
      <div class="fixed bottom-6 right-6">
        <button
          @click="saveDocument"
          class="px-4 py-2 bg-cyan-700/40 hover:bg-cyan-600/60 text-white rounded-lg shadow-lg backdrop-blur-sm transition-all duration-200 flex items-center gap-2 hover:scale-105 save-button"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5"
            viewBox="0 0 448 512"
            fill="currentColor"
          >
            <path
              d="M48 96l0 320c0 8.8 7.2 16 16 16l320 0c8.8 0 16-7.2 16-16l0-245.5c0-4.2-1.7-8.3-4.7-11.3l33.9-33.9c12 12 18.7 28.3 18.7 45.3L448 416c0 35.3-28.7 64-64 64L64 480c-35.3 0-64-28.7-64-64L0 96C0 60.7 28.7 32 64 32l245.5 0c17 0 33.3 6.7 45.3 18.7l74.5 74.5-33.9 33.9L320.8 84.7c-.3-.3-.5-.5-.8-.8L320 184c0 13.3-10.7 24-24 24l-192 0c-13.3 0-24-10.7-24-24L80 80 64 80c-8.8 0-16 7.2-16 16zm80-16l0 80 144 0 0-80L128 80zm32 240a64 64 0 1 1 128 0 64 64 0 1 1 -128 0z"
            />
          </svg>
          Save
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, nextTick, onMounted } from "vue";
import { useRoute } from "vue-router";
import { documentService, authService, fileService } from "../services/api";
import MarkdownIt from "markdown-it";
import hljs from "highlight.js";
import "highlight.js/styles/github-dark.css";
import DOMPurify from "dompurify";
import { v4 as uuidv4 } from "uuid";

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
  name: "MarkdownEditor",
  setup() {
    const route = useRoute();
    const textareaRef = ref(null);
    const previewRef = ref(null);
    const cursorPosition = ref(0);
    const isScrolling = ref(false);
    const documentTitle = ref("");
    const documentDescription = ref("");
    const documentAuthor = ref("");
    const lastModifiedDate = ref("");
    const markdown = ref("");
    const showEditModal = ref(false);
    const editingTitle = ref("");
    const editingDescription = ref("");
    const loadingUsernames = ref(new Set());
    const usernames = ref({});

    const renderedMarkdown = computed(() => {
      return DOMPurify.sanitize(md.render(markdown.value));
    });

    const fetchUsername = async (userId) => {
      if (!userId) {
        return "Unknown";
      }

      if (!usernames.value[userId] && !loadingUsernames.value.has(userId)) {
        loadingUsernames.value.add(userId);
        try {
          const username = await authService.getUserUsername(userId);
          usernames.value[userId] = username;
        } catch (error) {
          console.error(`Error fetching username for ${userId}:`, error);
          usernames.value[userId] = userId;
        } finally {
          loadingUsernames.value.delete(userId);
        }
      }
      return usernames.value[userId] || userId;
    };

    const authorUsername = computed(() => {
      return (
        usernames.value[documentAuthor.value] ||
        documentAuthor.value ||
        "Unknown"
      );
    });

    const updateCursor = () => {
      const textarea = textareaRef.value;
      if (textarea) {
        cursorPosition.value = textarea.selectionStart;
      }
    };

    const getCurrentCursorLine = (textarea) => {
      if (!textarea) return 1;
      const textToCursor = textarea.value.substring(0, textarea.selectionStart);
      return textToCursor.split("\n").length;
    };

    const getEditorTopVisibleLine = (textarea) => {
      if (!textarea) return 1;
      const computedStyle = getComputedStyle(textarea);
      let lineHeight = parseFloat(computedStyle.lineHeight);

      if (isNaN(lineHeight) || lineHeight === 0) {
        const fontSize = parseFloat(computedStyle.fontSize);
        lineHeight = !isNaN(fontSize) && fontSize > 0 ? fontSize * 1.2 : 16;
      }
      if (lineHeight <= 0) lineHeight = 16;

      const linesScrolled = textarea.scrollTop / lineHeight;
      return Math.max(1, Math.floor(linesScrolled) + 1);
    };

    const findClosestElementInPreview = (targetLineZeroIndexed, preview) => {
      const elements = Array.from(
        preview.querySelectorAll(
          ["[data-line]", "img[data-line]", "table tr[data-line]"].join(",")
        )
      );

      if (elements.length === 0) return null;

      let bestElement = null;
      let bestElementLine = -1;
      let bestDistance = Infinity;

      for (const element of elements) {
        const elementLine = parseInt(element.getAttribute("data-line"), 10);
        const distance = Math.abs(elementLine - targetLineZeroIndexed);

        if (elementLine <= targetLineZeroIndexed) {
          if (
            elementLine > bestElementLine ||
            (elementLine === bestElementLine && distance < bestDistance)
          ) {
            bestElement = element;
            bestElementLine = elementLine;
            bestDistance = distance;
          }
        }
      }

      return bestElement || elements[0];
    };

    const syncScrollInternal = (scrollTargetType = "viewport") => {
      if (isScrolling.value) return;

      const textarea = textareaRef.value;
      const preview = previewRef.value;
      if (!textarea || !preview) return;

      isScrolling.value = true;

      try {
        const editorScrollPercent =
          textarea.scrollTop / (textarea.scrollHeight - textarea.clientHeight);

        const previewScrollHeight = preview.scrollHeight - preview.clientHeight;

        preview.scrollTop = previewScrollHeight * editorScrollPercent;

        requestAnimationFrame(() => {
          setTimeout(() => {
            isScrolling.value = false;
          }, 50);
        });
      } catch (e) {
        console.error("Scroll sync error:", e);
        isScrolling.value = false;
      }
    };

    const debounce = (fn, delay) => {
      let timeoutId;
      return (...args) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn(...args), delay);
      };
    };

    const debouncedViewportSync = debounce(
      () => syncScrollInternal("viewport"),
      16
    );

    const handleDrop = async (event) => {
      try {
        const files = Array.from(event.dataTransfer.files).filter((file) =>
          file && file.type && file.type.startsWith("image/")
        );
        
        if (files.length === 0) {
          console.warn("No valid image files found");
          return;
        }

        event.preventDefault();
        event.stopPropagation();

        const textarea = textareaRef.value;
        if (textarea) textarea.focus();

        for (const file of files) {
          const loadingText = `![Uploading ${file.name}...]()\n`;
          try {
            // Add loading indicator before upload
            insertText(loadingText);

            const imageUrl = await uploadImage(file);
            
            // Replace loading text with actual image
            markdown.value = markdown.value.replace(
              loadingText,
              `![${file.name}](${imageUrl})\n`
            );
          } catch (error) {
            console.error(`Failed to upload image: ${file.name}`, error);
            // Remove loading text on error
            markdown.value = markdown.value.replace(loadingText, '');
          }
        }
      } catch (error) {
        console.error("Error handling file drop:", error);
      }
    };

    // Helper function to insert text at cursor position
    const insertText = (text) => {
      const textarea = textareaRef.value;
      const pos = cursorPosition.value;
      const before = markdown.value.substring(0, pos);
      const after = markdown.value.substring(pos);
      markdown.value = `${before}${text}${after}`;
      
      // Update cursor position
      textarea.focus();
      const newPos = pos + text.length;
      textarea.setSelectionRange(newPos, newPos);
      cursorPosition.value = newPos;
    };

    const uploadImage = async (file) => {
      // Get user token first
      const token = localStorage.getItem("jwtToken");
      if (!token) {
        throw new Error('Authentication required');
      }

      try {
        // Validate file
        if (!file || !file.name) {
          throw new Error('Invalid file object');
        }

        // Parse token to get uid
        const payload = JSON.parse(atob(token.split(".")[1]));
        const uid = payload.uid;

        if (!uid) {
          throw new Error('User ID not found in token');
        }

        // Get file extension with fallback
        const fileNameParts = file.name.split('.');
        const fileExt = fileNameParts.length > 1 ? fileNameParts.pop() : 'png';
        
        // Generate unique filename
        const uuid = uuidv4();
        const filename = `${uuid}.${fileExt}`;

        // Get upload URL
        const { url: uploadUrl } = await fileService.generateUploadUrl(uid, filename);

        if (!uploadUrl) {
          throw new Error('Failed to get upload URL');
        }

        const response = await fetch(uploadUrl, {
          method: "PUT",
          headers: {
            "Content-Type": file.type || 'image/png',
          },
          body: file,
        });

        if (!response.ok) {
          throw new Error(`Upload failed: ${response.statusText}`);
        }

        return `${import.meta.env.VITE_API_BASE_URL}minio-api/files/${uid}/${filename}`;
      } catch (error) {
        console.error("Error uploading image:", error);
        throw error;
      }
    };

    const insertMarkdownImage = (url) => {
      const textarea = textareaRef.value;
      const pos = cursorPosition.value;
      const before = markdown.value.substring(0, pos);
      const after = markdown.value.substring(pos);
      const insertText = `![Image](${url})\n`;
      markdown.value = `${before}${insertText}${after}`;

      textarea.focus();
      const newPos = pos + insertText.length;
      textarea.setSelectionRange(newPos, newPos);
      cursorPosition.value = newPos;
    };

    const saveMetadata = async () => {
      try {
        documentTitle.value = editingTitle.value;
        documentDescription.value = editingDescription.value;
        const { data } = await documentService.updateDocumentMetadata(
          route.params.id,
          {
            title: editingTitle.value,
            description: editingDescription.value,
          }
        );
        showEditModal.value = false;
      } catch (error) {
        console.error("Error saving metadata:", error);
      }
    };

    const fetchDocument = async () => {
      try {
        const documentId = route.params.id;
        const { data } = await documentService.getDocumentDetail(documentId);

        documentTitle.value = data.title || "";
        documentDescription.value = data.description || "";
        editingTitle.value = data.title || "";
        editingDescription.value = data.description || "";

        const formatDate = (dateString) => {
          if (!dateString) return "Not available";
          const date = new Date(dateString);
          const year = date.getFullYear();
          const month = String(date.getMonth() + 1).padStart(2, "0");
          const day = String(date.getDate()).padStart(2, "0");
          return `${year}/${month}/${day}`;
        };

        documentAuthor.value = data.creator_id
          ? `${data.creator_id}`
          : "Unknown";
        lastModifiedDate.value = formatDate(data.updated_at);

        if (data.creator_id) {
          await fetchUsername(data.creator_id);
          // console.log("Fetched author username:", authorUsername.value);
        }

        if (data.url) {
          const content = await documentService.getMarkdownContent(data.url);
          markdown.value = content;
        }
      } catch (error) {
        console.error("Error fetching document:", error);
      }
    };

    onMounted(() => {
      fetchDocument();
    });

    watch(renderedMarkdown, () => {
      nextTick(() => {
        syncScrollInternal("cursor");
      });
    });

    const handleScroll = (event) => {
      if (!isScrolling.value) {
        requestAnimationFrame(() => {
          syncScrollInternal("viewport");
        });
      }
    };

    const saveDocument = async () => {
      try {
        const documentId = route.params.id;
        const { data } = await documentService.updateDocument(documentId);

        // Upload content to Minio URL
        if (data.url) {
          const response = await fetch(data.url, {
            method: "PUT",
            headers: {
              "Content-Type": "text/markdown",
            },
            body: markdown.value,
          });

          if (!response.ok) {
            throw new Error("Failed to upload to Minio");
          }
        }

        // Update document metadata if needed
        // await documentService.updateDocument(documentId, {
        //   content: markdown.value,
        // });

        // Show success indication
        const button = document.querySelector(".save-button");
        button.classList.add("save-success");
        setTimeout(() => {
          button.classList.remove("save-success");
        }, 2000);
      } catch (error) {
        console.error("Error saving document:", error);
        const button = document.querySelector(".save-button");
        button.classList.add("save-error");
        setTimeout(() => {
          button.classList.remove("save-error");
        }, 2000);
      }
    };

    return {
      markdown,
      renderedMarkdown,
      textareaRef,
      previewRef,
      cursorPosition,
      handleDrop,
      updateCursor,
      handleScroll,
      saveDocument,
      showEditModal,
      editingTitle,
      editingDescription,
      saveMetadata,
      documentTitle,
      documentDescription,
      documentAuthor,
      lastModifiedDate,
      fetchUsername,
      authorUsername,
      usernames,
      loadingUsernames,
    };
  },
};
</script>

<style>
textarea::-webkit-scrollbar {
  width: 8px;
}

textarea::-webkit-scrollbar-thumb {
  background-color: #4b5563;
  border-radius: 6px;
}

.save-success {
  background-color: rgba(22, 163, 74, 0.6); /* bg-green-600/80 */
  transform: scale(1.05);
}

.save-error {
  background-color: rgba(220, 38, 38, 0.6); /* bg-red-600/80 */
  animation: shake 0.5s ease-in-out;
}

@keyframes shake {
  0%,
  100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(-5px);
  }
  75% {
    transform: translateX(5px);
  }
}
</style>
