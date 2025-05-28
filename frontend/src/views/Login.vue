<template>
  <div class="text-gray-800 p-6">
    <div class="max-w-7xl mx-auto text-center">
      <h2
        class="text-3xl font-bold mb-6 tracking-wide border-b border-gray-300 pb-6"
      >
        Login
      </h2>

      <div class="my-6 max-w-md mx-auto">
        <div>
          <div class="mb-4">
            <label for="username" class="block mb-2 text-gray-700 font-medium">
              Username
            </label>
            <input
              id="username"
              type="text"
              v-model="username"
              placeholder="Enter your username"
              class="w-full px-3 py-2 border rounded text-gray-700 focus:outline-none focus:bg-gray-100 hover:shadow-lg hover:bg-gray-50 transition duration-200"
            />
          </div>

          <div class="mb-6">
            <label for="password" class="block mb-2 text-gray-700 font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              v-model="password"
              placeholder="Enter your password"
              class="w-full px-3 py-2 border rounded text-gray-700 focus:outline-none focus:bg-gray-100 hover:shadow-lg hover:bg-gray-50 transition duration-200"
            />
          </div>

          <button
            @click="localLogin"
            :disabled="!username || !password"
            class="w-full border border-gray-600 text-gray-600 font-bold py-2 px-4 rounded transition-colors duration-200 hover:bg-gray-100 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none"
          >
            Login
          </button>
        </div>

        <div class="flex items-center mt-6">
          <hr class="flex-grow border-t border-gray-300" />
          <span class="mx-2 text-gray-400">OR</span>
          <hr class="flex-grow border-t border-gray-300" />
        </div>

        <div class="mt-6 text-center">
          <button
            v-if="!isTokenReceived"
            @click="NYCUOAuthLogin"
            class="w-full border border-cyan-700 text-cyan-700 font-bold py-2 px-4 rounded transition-colors duration-200 hover:bg-gray-100 flex items-center justify-center transform hover:scale-105"
          >
            <img
              src="/images/nycu-oauth.svg"
              alt="NYCU Logo"
              class="w-6 h-6 mr-1"
            />
            NYCU OAuth
          </button>
          <button
            v-if="!isTokenReceived"
            @click="CSITOAuthLogin"
            class="mt-4 w-full border border-cyan-700 text-cyan-700 font-bold py-2 px-4 rounded transition-colors duration-200 hover:bg-gray-100 flex items-center justify-center transform hover:scale-105"
          >
            <img
              src="/images/csit-oauth.svg"
              alt="CSIT Logo"
              class="w-6 h-6 mr-1"
            />
            CSIT OAuth
          </button>
          <p v-else class="mt-2 text-green-600 font-semibold">
            Login successful. Redirecting...
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { authStore } from "../store/auth";

export default {
  name: "Login",
  setup() {
    const apiBase = import.meta.env.VITE_API_BASE_URL;
    const router = useRouter();

    const username = ref("");
    const password = ref("");
    const isTokenReceived = ref(false);

    onMounted(() => {
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get("token");
      if (token) {
        authStore.setToken(token);
        isTokenReceived.value = true;
        router.replace({ name: "Home" });
      }
    });

    const localLogin = async () => {
      try {
        if (!username.value.trim() || !password.value.trim()) {
          alert("Username and password cannot be empty.");
          return;
        }

        const formData = new URLSearchParams();
        formData.append("username", username.value);
        formData.append("password", password.value);

        const response = await fetch(`${apiBase}/login`, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: formData,
        });

        if (!response.ok) {
          throw new Error(
            "Login failed. Please check your username and password."
          );
        }

        const data = await response.json();
        if (data.access_token) {
          authStore.setToken(data.access_token);
          router.replace({ name: "Home" });
        }
      } catch (error) {
        console.error(error);
        alert(error.message);
      }
    };

    const NYCUOAuthLogin = () => {
      window.location.href = `${apiBase}/oauth/nycu/login`;
    };

    const CSITOAuthLogin = () => {
      window.location.href = `${apiBase}/oauth/csit/login`;
    };

    return {
      username,
      password,
      isTokenReceived,
      localLogin,
      NYCUOAuthLogin,
      CSITOAuthLogin,
    };
  },
};
</script>

<style scoped></style>
