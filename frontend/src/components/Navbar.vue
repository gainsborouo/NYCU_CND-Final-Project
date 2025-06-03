<template>
  <nav class="fixed top-0 left-0 right-0 z-50 bg-gray-900 py-3 shadow-md">
    <div class="container mx-auto flex items-center justify-between px-4">
      <!-- Logo/Brand -->
      <router-link to="/" class="text-2xl font-bold text-gray-200">
        Document Center
      </router-link>

      <!-- Right side navigation items -->
      <div class="flex items-center space-x-6">
        <!-- Notification Icon -->
        <router-link
          v-if="isLoggedIn"
          to="/notifications"
          class="text-gray-300 hover:text-cyan-500 transition-colors duration-200 relative"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
            />
          </svg>
          <!-- Add this badge when there are unread notifications -->
          <!-- <span class="absolute -top-1 -right-1 bg-red-500 rounded-full w-4 h-4 text-xs flex items-center justify-center text-white">3</span> -->
        </router-link>

        <!-- Login Link (when not logged in) -->
        <div v-if="!isLoggedIn" class="relative">
          <router-link
            to="/login"
            class="flex items-center space-x-2 text-gray-200 px-3 py-2 rounded-md hover:bg-gray-800 transition-colors duration-200 h-9"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"
              />
            </svg>
            <!-- <span>Login</span> -->
          </router-link>
        </div>

        <!-- User Dropdown (when logged in) -->
        <div v-else class="relative" ref="dropdownContainer">
          <div
            @click.stop="toggleDropdown"
            class="flex items-center space-x-2 cursor-pointer py-2 px-3 rounded-md hover:bg-gray-800 transition-colors duration-200 h-9"
          >
            <!-- User avatar (optional) -->
            <!-- <div
              class="bg-cyan-700 text-white rounded-full w-8 h-8 flex items-center justify-center"
            >
              {{ username.charAt(0).toUpperCase() }}
            </div> -->
            <span class="text-gray-200">{{ username }}</span>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              :class="{ 'transform rotate-180': isDropdownOpen }"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>

          <!-- Dropdown Menu -->
          <div
            v-show="isDropdownOpen"
            class="absolute right-0 mt-2 w-48 bg-gray-800 rounded-md shadow-lg py-1 z-50 border border-gray-700"
          >
            <button
              @click="logout"
              class="w-full text-left px-4 py-2 text-gray-200 hover:bg-gray-700 transition-colors duration-150 flex items-center space-x-2"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                />
              </svg>
              <span>Logout</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </nav>
</template>

<script>
import { computed, ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { authStore } from "../store/auth";

export default {
  name: "Navbar",
  setup() {
    const router = useRouter();
    const isLoggedIn = computed(() => !!authStore.token);
    const isDropdownOpen = ref(false);
    const dropdownContainer = ref(null);

    const username = computed(() => {
      if (!authStore.token) return "";
      try {
        const payload = JSON.parse(atob(authStore.token.split(".")[1]));
        return payload.username;
      } catch (error) {
        return "";
      }
    });

    const toggleDropdown = (event) => {
      event.stopPropagation();
      isDropdownOpen.value = !isDropdownOpen.value;
    };

    const closeDropdown = (e) => {
      // Only close if click is outside the dropdown container
      if (
        dropdownContainer.value &&
        !dropdownContainer.value.contains(e.target)
      ) {
        isDropdownOpen.value = false;
      }
    };

    // Close dropdown when clicking outside
    onMounted(() => {
      document.addEventListener("click", closeDropdown);
    });

    onUnmounted(() => {
      document.removeEventListener("click", closeDropdown);
    });

    const logout = () => {
      authStore.setToken(null);
      router.push({ name: "Home" });
      isDropdownOpen.value = false;
    };

    return {
      isLoggedIn,
      username,
      logout,
      isDropdownOpen,
      toggleDropdown,
      dropdownContainer,
    };
  },
};
</script>

<style scoped>
.container {
  max-width: 1280px;
}
</style>
