<template>
  <div class="text-gray-800 p-6">
    <div class="max-w-7xl mx-auto text-center">
      <h2
        class="text-3xl font-bold mb-6 tracking-wide border-b border-gray-300 pb-6"
      >
        Document Center
      </h2>

      <div v-if="isLoggedIn" class="my-6">
        <h2 class="text-2xl font-bold pb-4 text-gray-700">Available Courses</h2>
        <div class="max-w-xl mx-auto overflow-x-auto rounded-lg shadow-md">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-100">
              <tr>
                <th
                  scope="col"
                  class="px-6 py-4 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider"
                >
                  ID
                </th>
                <th
                  scope="col"
                  class="px-6 py-4 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider"
                >
                  Name
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr
                v-for="course in courses"
                :key="course.id"
                class="hover:bg-gray-50 transition-colors duration-200"
              >
                <td class="px-6 py-4 whitespace-nowrap text-center">
                  <span class="text-sm font-medium text-gray-900">{{
                    course.id
                  }}</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-center">
                  <span class="text-sm text-gray-900">{{ course.name }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-else class="my-6">
        <p class="mb-4">
          You are not logged in. Please go to the
          <router-link to="/login" class="underline">Login</router-link>
          page.
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from "vue";
import axios from "axios";
import { authStore } from "../store/auth";

export default {
  name: "Home",
  setup() {
    const isLoggedIn = computed(() => !!authStore.token);
    const courses = ref([]);
    const apiBase = import.meta.env.VITE_API_BASE_URL;

    const fetchCourses = async () => {
      try {
        const response = await axios.get(`${apiBase}/courses`, {
          headers: {
            Authorization: `Bearer ${authStore.token}`,
          },
        });
        courses.value = response.data;
      } catch (error) {
        console.error("Failed to fetch courses", error);
      }
    };

    onMounted(() => {
      if (isLoggedIn.value) {
        fetchCourses();
      }
    });

    return {
      isLoggedIn,
      courses,
    };
  },
};
</script>

<style scoped></style>
