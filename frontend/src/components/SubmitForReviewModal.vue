<template>
  <Transition
    enter-active-class="transition duration-300 ease-out"
    enter-from-class="transform opacity-0"
    enter-to-class="transform opacity-100"
    leave-active-class="transition duration-200 ease-in"
    leave-from-class="transform opacity-100"
    leave-to-class="transform opacity-0"
  >
    <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="fixed inset-0 bg-gray-950/90 backdrop-blur-sm" @click="$emit('close')"></div>
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md relative z-10">
        <h3 class="text-xl font-semibold mb-4">Submit for Review</h3>
        <form @submit.prevent="handleSubmit">
          <div class="mb-6">
            <label class="block text-sm font-medium mb-2">Select Reviewer</label>
            <select
              v-model="selectedReviewerId"
              class="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
              required
            >
              <option value="" disabled>Select a reviewer</option>
              <option
                v-for="reviewer in reviewers"
                :key="reviewer.id"
                :value="reviewer.id"
              >
                {{ reviewer.username }}
              </option>
            </select>
            <div v-if="error" class="text-red-500 text-sm mt-2">
              {{ error }}
            </div>
          </div>
          <div class="flex justify-end gap-3">
            <button
              type="button"
              @click="$emit('close')"
              class="px-4 py-2 text-gray-300 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="!selectedReviewerId"
              class="px-4 py-2 bg-cyan-700 text-white rounded-lg hover:bg-cyan-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Submit
            </button>
          </div>
        </form>
      </div>
    </div>
  </Transition>
</template>

<script>
import { ref, watch, computed, onMounted } from 'vue';
import { authService, documentService } from '../services/api';

export default {
  name: 'SubmitForReviewModal',
  props: {
    show: Boolean,
    documentId: Number,
    groupId: String,
  },
  emits: ['close', 'submitted'],
  
  setup(props, { emit }) {
    const reviewersData = ref({});
    const selectedReviewerId = ref('');
    const error = ref(null);

    const reviewers = computed(() => {
      return Object.entries(reviewersData.value).map(([id, username]) => ({
        id: Number(id),
        username
      }));
    });

    const loadReviewers = async () => {
      if (!props.groupId) return;
      
      try {
        const data = await authService.getGroupReviewers(props.groupId);
        reviewersData.value = data;
      } catch (err) {
        console.error('Error loading reviewers:', err);
        error.value = 'Failed to load reviewers';
      }
    };

    const handleSubmit = async () => {
      if (!selectedReviewerId.value) return;
      
      try {
        await documentService.submitForReview(props.documentId, selectedReviewerId.value);
        emit('submitted');
        emit('close');
        selectedReviewerId.value = '';
      } catch (err) {
        console.error('Error submitting for review:', err);
        error.value = 'Failed to submit for review';
      }
    };

    watch(() => props.show, (newValue) => {
      if (!newValue) {
        selectedReviewerId.value = '';
        error.value = null;
      } else {
        loadReviewers();
      }
    });

    onMounted(() => {
      if (props.show) {
        loadReviewers();
      }
    });

    return {
      reviewers,
      selectedReviewerId,
      error,
      handleSubmit,
    };
  },
};
</script>