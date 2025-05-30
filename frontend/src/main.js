import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import axios from "axios";
import "./assets/styles.css";
import { authStore } from "./store/auth";

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      authStore.setToken(null);
      window.alert("Your session has expired. Please log in again to continue.");
      window.location.href = "/";
    }
    return Promise.reject(error);
  }
);

createApp(App).use(router).mount("#app");
