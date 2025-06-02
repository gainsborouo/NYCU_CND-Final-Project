<template>
  <div class="flex h-[calc(100vh-3.5rem)] bg-gray-950 text-gray-100 font-sans">
    <div class="w-full flex items-center justify-center p-6">
      <div class="w-full max-w-md bg-gray-900 rounded-lg p-8 shadow-xl border border-gray-700">
        <h2 class="text-3xl font-bold mb-6 text-center text-gray-100">
          Login
        </h2>

        <form @submit.prevent="localLogin" class="space-y-6">
          <div>
            <label for="username" class="block mb-2 text-gray-200 font-medium">
              Username
            </label>
            <input
              id="username"
              type="text"
              v-model="username"
              placeholder="Enter your username"
              class="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-100 
                     focus:outline-none focus:border-cyan-700 focus:ring-1 focus:ring-cyan-700 
                     transition duration-200"
            />
          </div>

          <div>
            <label for="password" class="block mb-2 text-gray-200 font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              v-model="password"
              placeholder="Enter your password"
              class="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-100 
                     focus:outline-none focus:border-cyan-700 focus:ring-1 focus:ring-cyan-700 
                     transition duration-200"
            />
          </div>

          <button
            type="submit"
            :disabled="!username || !password"
            class="w-full bg-cyan-700 text-white font-bold py-2 px-4 rounded-lg
                   transition-colors duration-200 hover:bg-cyan-600
                   disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Sign in
          </button>

          <div class="flex items-center my-6">
            <hr class="flex-grow border-t border-gray-700" />
            <span class="px-4 text-gray-500">OR</span>
            <hr class="flex-grow border-t border-gray-700" />
          </div>

          <div class="space-y-4">
            <button
              v-if="!isTokenReceived"
              @click="GoogleOAuthLogin"
              class="w-full border border-cyan-700 text-cyan-700 font-bold py-2 px-4 rounded-lg 
                     transition-colors duration-200 hover:bg-cyan-700 hover:text-white
                     flex items-center justify-center"
            >
              <img
                src="/images/google-oauth.webp"
                alt="Google Logo"
                class="w-6 h-6 mr-2"
              />
              Google OAuth
            </button>

            <p v-if="isTokenReceived" class="text-center text-cyan-500 font-semibold">
              Login successful. Redirecting...
            </p>
          </div>
        </form>
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

        const response = await fetch(`${apiBase}/auth/login`, {
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

    const GoogleOAuthLogin = () => {
      window.location.href = `${apiBase}/auth/oauth/google/login`;
    };

    return {
      username,
      password,
      isTokenReceived,
      localLogin,
      GoogleOAuthLogin,
    };
  },
};
</script>

<style scoped></style>