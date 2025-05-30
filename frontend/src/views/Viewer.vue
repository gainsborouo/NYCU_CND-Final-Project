<template>
  <div class="min-h-[calc(100vh-3.5rem)] bg-gray-950 text-gray-100 font-sans">
    <div class="max-w-4xl mx-auto p-6">
      <!-- Document Header -->
      <div class="flex justify-between items-start mb-8">
        <div>
          <h1 class="text-3xl font-bold mb-2">{{ document.title }}</h1>
          <div class="flex items-center gap-3 text-sm text-gray-400 py-2">
            <span class="text-cyan-500">{{ document.type }}</span>
            <span>•</span>
            <span>Last edited {{ document.lastEdited }}</span>
          </div>
        </div>
        <span
          :class="getStatusClass(document.status)"
          class="px-3 py-1 rounded-full text-xs"
        >
          {{ document.status }}
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
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
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
  name: "DocumentViewer",
  setup() {
    const route = useRoute();
    const document = ref({
      id: route.params.id,
      title: "Manufacturing Process Documentation",
      lastEdited: "2024-05-29",
      type: "Markdown",
      status: "Published",
      content: `# Manufacturing Process Overview

## Introduction
This document outlines the standard operating procedures for our manufacturing process.

## Steps
1. **Material Preparation**
   - Check raw materials quality
   - Prepare workstation
   
2. **Assembly Process**
   - Follow assembly sequence
   - Perform quality checks

### Code Example
\`\`\`javascript
function checkQuality(item) {
  return item.quality >= standardLevel;
}
\`\`\`
`,
    });

    const renderedContent = ref("");

    onMounted(() => {
      renderedContent.value = DOMPurify.sanitize(
        md.render(document.value.content)
      );
    });

    const getStatusClass = (status) => {
      const classes = {
        Draft: "bg-gray-600 text-white",
        "Pending Review": "bg-yellow-600 text-white",
        Published: "bg-green-600 text-white",
        Rejected: "bg-red-600 text-white",
      };
      return classes[status] || "bg-gray-600 text-white";
    };

    return {
      document,
      renderedContent,
      getStatusClass,
    };
  },
};
</script>

<style scoped></style>
