<template>
  <div class="flex h-[calc(100vh-3.5rem)] bg-gray-900 text-gray-100 font-sans">
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
  </div>
</template>

<script>
import { ref, computed, watch, nextTick } from "vue";
import MarkdownIt from "markdown-it";
import hljs from "highlight.js";
import "highlight.js/styles/github-dark.css";
import DOMPurify from "dompurify";

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
    const markdown = ref(
      `# Welcome\n\n### 使用組件\n\n在主應用組件中使用 Greeting 組件：\n\n\`\`\`jsx\n// src/App.jsx\nimport React from "react";\nimport Greeting from "./components/Greeting";\n\nfunction App() {\n  return (\n    <div className="App">\n      <Greeting name="Alice" />\n      <Greeting name="Bob" />\n    </div>\n  );\n}\n\`\`\``
    );

    const textareaRef = ref(null);
    const previewRef = ref(null);
    const cursorPosition = ref(0);
    const isScrolling = ref(false);
    const scrollTimeout = ref(null);
    const lastScrollTop = ref(0);

    const renderedMarkdown = computed(() => {
      return DOMPurify.sanitize(md.render(markdown.value));
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
      const files = Array.from(event.dataTransfer.files).filter((file) =>
        file.type.startsWith("image/")
      );
      if (files.length === 0) return;

      event.preventDefault();
      event.stopPropagation();

      const textarea = textareaRef.value;
      if (textarea) textarea.focus();

      for (const file of files) {
        const imageUrl = await uploadImage(file);
        insertMarkdownImage(imageUrl);
      }
    };

    const uploadImage = async (file) => {
      return "https://cdn.example.com/image.jpg";
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

    return {
      markdown,
      renderedMarkdown,
      textareaRef,
      previewRef,
      handleDrop,
      updateCursor,
      handleScroll,
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

.prose pre {
  overflow-x: auto;
  padding: 0.75rem;
  border-radius: 0.375rem;
  background-color: #1e1e1e;
  color: #f3f3f3;
}

.prose code {
  background-color: #1e1e1e;
  padding: 0.2em 0.4em;
  border-radius: 0.25rem;
  font-size: 0.95em;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.prose code::before,
.prose code::after {
  content: none;
}

.prose img {
  margin-top: 1.5em;
  margin-bottom: 1.5em;
  display: block;
  max-width: 100%;
  height: auto;
}

.prose table {
  margin-top: 1.5em;
  margin-bottom: 1.5em;
  width: 100%;
  border-collapse: collapse;
}

.prose th,
.prose td {
  padding: 0.75rem;
  border: 1px solid #4a5568;
}

.prose > * {
  line-height: 1.6;
  margin-top: 0.5em;
  margin-bottom: 0.5em;
  position: relative;
}

.prose {
  scroll-behavior: smooth;
  overflow-y: auto;
}

.prose [data-line] {
  position: relative;
  min-height: 1.6em;
}
</style>
