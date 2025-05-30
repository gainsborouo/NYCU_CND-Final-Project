<template>
  <div class="min-h-[calc(100vh-3.5rem)] bg-gray-950 text-gray-100">
    <div class="grid grid-cols-2 h-full">
      <!-- Document Preview -->
      <div class="border-r border-gray-700 p-6 overflow-auto">
        <div class="max-w-2xl mx-auto">
          <h1 class="text-2xl font-bold mb-6">{{ document.title }}</h1>
          <div class="prose prose-invert max-w-none">
            <div v-html="renderedContent"></div>
          </div>
        </div>
      </div>

      <!-- Review Panel -->
      <div class="p-6 bg-gray-900">
        <div class="max-w-2xl mx-auto">
          <h2 class="text-xl font-bold mb-6">Review</h2>

          <!-- Review Form -->
          <div class="space-y-6">
            <div>
              <label class="block text-sm font-medium text-gray-300 mb-2">
                Decision
              </label>
              <div class="flex gap-4">
                <button
                  @click="decision = 'approve'"
                  :class="[
                    'px-4 py-2 rounded-lg font-medium',
                    decision === 'approve'
                      ? 'bg-green-600 text-white'
                      : 'border border-gray-600 text-gray-400',
                  ]"
                >
                  Approve
                </button>
                <button
                  @click="decision = 'reject'"
                  :class="[
                    'px-4 py-2 rounded-lg font-medium',
                    decision === 'reject'
                      ? 'bg-red-600 text-white'
                      : 'border border-gray-600 text-gray-400',
                  ]"
                >
                  Reject
                </button>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-300 mb-2">
                Comments
              </label>
              <textarea
                v-model="comments"
                rows="4"
                class="w-full px-3 py-2 bg-gray-800 text-gray-100 rounded-lg border border-gray-700"
                placeholder="Add your review comments here..."
              ></textarea>
            </div>

            <button
              @click="submitReview"
              :disabled="!decision || (decision === 'reject' && !comments)"
              class="w-full bg-cyan-700 text-white py-2 rounded-lg hover:bg-cyan-600 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Submit Review
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from "vue";
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

export default {
  name: "DocumentReview",
  setup() {
    const route = useRoute();
    const document = ref({
      id: route.params.id,
      title: "Safety Guidelines Update 2024",
      type: "Policy",
      author: "John Doe",
      lastEdited: "2024-05-28",
      status: "Pending Review",
      content: `# Safety Guidelines 2024

## Overview
This document outlines updated safety procedures for all laboratory operations.

## Key Changes
1. **Personal Protective Equipment**
   - Safety goggles must be worn at all times
   - Lab coats required for all chemical handling

2. **Emergency Procedures**
   - Updated evacuation routes
   - New emergency contact numbers

### Code Implementation
\`\`\`python
def check_safety_compliance(area_id):
    required_equipment = get_required_equipment(area_id)
    current_equipment = scan_current_equipment(area_id)
    
    return all(item in current_equipment for item in required_equipment)
\`\`\`

## Review Notes
- Implementation timeline
- Staff training requirements
- Budget considerations`,
    });

    const decision = ref("");
    const comments = ref("");
    const renderedContent = computed(() => {
      return DOMPurify.sanitize(md.render(document.value.content));
    });

    const submitReview = async () => {
      console.log("Submitting review:", {
        documentId: document.value.id,
        decision: decision.value,
        comments: comments.value,
      });
      // TODO: Implement actual API call
    };

    return {
      document,
      decision,
      comments,
      renderedContent,
      submitReview,
    };
  },
};
</script>
