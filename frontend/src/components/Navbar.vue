<template>
  <nav class="fixed top-0 left-0 right-0 z-50 bg-gray-900 px-8 py-3">
    <div class="mx-auto flex items-center justify-between px-10">
      <router-link to="/" class="text-2xl font-bold text-gray-200 w-60">
        Document Center
      </router-link>

      <div class="flex-1 flex justify-center space-x-8">
        <router-link
          to="/"
          class="text-gray-200 hover:text-cyan-700 transition-colors duration-300"
        >
          Home
        </router-link>
        <router-link
          to="/editor"
          class="text-gray-200 hover:text-cyan-700 transition-colors duration-300"
        >
          Editor
        </router-link>
        <router-link
          to="/viewer"
          class="text-gray-200 hover:text-cyan-700 transition-colors duration-300"
        >
          Viewer
        </router-link>
        <router-link
          to="/notifications"
          class="text-gray-200 hover:text-cyan-700 transition-colors duration-300"
        >
          Notifications
        </router-link>
        <router-link
          to="/review"
          class="text-gray-200 hover:text-cyan-700 transition-colors duration-300"
        >
          Review
        </router-link>
      </div>

      <div class="flex items-center w-60 justify-end">
        <div v-if="!isLoggedIn" class="flex space-x-4">
          <router-link
            to="/login"
            class="text-gray-200 hover:text-cyan-700 transition-colors duration-300"
          >
            Login
          </router-link>
        </div>
        <div v-else class="flex items-center space-x-4">
          <span class="text-gray-200">{{ username }}</span>
          <button
            @click="logout"
            class="border border-cyan-700 text-cyan-700 px-3 py-1 rounded hover:bg-cyan-700 hover:text-black transition-all duration-300"
          >
            Logout
          </button>
        </div>
      </div>
    </div>
  </nav>
</template>

<script>
import { computed } from "vue";
import { useRouter } from "vue-router";
import { authStore } from "../store/auth";

export default {
  name: "Navbar",
  setup() {
    const router = useRouter();
    const isLoggedIn = computed(() => !!authStore.token);
    const username = computed(() => {
      if (!authStore.token) return "";
      try {
        const payload = JSON.parse(atob(authStore.token.split(".")[1]));
        return payload.username;
      } catch (error) {
        return "";
      }
    });

    const logout = () => {
      authStore.setToken(null);
      router.push({ name: "Home" });
    };

    return { isLoggedIn, username, logout };
  },
};
</script>