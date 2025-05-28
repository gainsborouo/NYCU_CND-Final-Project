import { createRouter, createWebHistory } from "vue-router";
import Home from "../views/Home.vue";
import Login from "../views/Login.vue";
import MarkdownEditor from "../views/MarkdownEditor.vue";

const routes = [
  {
    path: "/",
    name: "Home",
    component: Home,
  },
  {
    path: "/login",
    name: "Login",
    component: Login,
  },
  {
    path: "/document",
    name: "MarkdownEditor",
    component: MarkdownEditor,
  },
//   {
//     path: "/logviewer",
//     name: "LogViewer",
//     component: LogViewer,
//     meta: { requiresAuth: true },
//   },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

// router.beforeEach((to, from, next) => {
//   const token = localStorage.getItem("jwtToken");
//   if (to.meta.requiresAuth) {
//     if (!token) {
//       next({ name: "Login" });
//     } else {
//       next();
//     }
//   } else {
//     if (to.name === "Login" && token) {
//       next({ name: "Home" });
//     } else {
//       next();
//     }
//   }
// });

export default router;
