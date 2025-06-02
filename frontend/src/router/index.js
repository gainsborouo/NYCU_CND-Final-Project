import { createRouter, createWebHistory } from "vue-router";
import Home from "../views/Home.vue";
import Login from "../views/Login.vue";
import Editor from "../views/Editor.vue";
import Viewer from "../views/Viewer.vue";
import Notifications from "../views/Notifications.vue";
import Review from "../views/Review.vue";

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
    path: "/editor/:id",
    name: "Editor",
    component: Editor,
    meta: { requiresAuth: true },
    props: true,
  },
  {
    path: "/viewer/:id",
    name: "Viewer",
    component: Viewer,
    meta: { requiresAuth: true },
    props: true,
  },
  {
    path: "/notifications",
    name: "Notifications",
    component: Notifications,
    meta: { requiresAuth: true },
  },
  {
    path: "/review/:id",
    name: "Review",
    component: Review,
    meta: { requiresAuth: true },
    props: true,
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem("jwtToken");
  if (to.meta.requiresAuth) {
    if (!token) {
      next({ name: "Login" });
    } else {
      next();
    }
  } else {
    if (to.name === "Login" && token) {
      next({ name: "Home" });
    } else {
      next();
    }
  }
});

export default router;
