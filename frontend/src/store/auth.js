import { reactive } from "vue";

export const authStore = reactive({
  token: localStorage.getItem("jwtToken") || null,
  setToken(newToken) {
    this.token = newToken;
    if (newToken) {
      localStorage.setItem("jwtToken", newToken);
    } else {
      localStorage.removeItem("jwtToken");
    }
  },
});
