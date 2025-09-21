// router/index.js
import { createRouter, createWebHistory } from "vue-router";
import UserLogin from "@/components/UserLogin.vue";
import UserLayout from "@/views/UserLayout.vue"; // 新增布局组件
import UserDashboard from "@/views/UserDashboard.vue";
import UserInfo from "@/views/UserInfo.vue";
import UserList from "@/views/UserList.vue";
import BigdataUser from "@/views/BigdataUser.vue";
import PasswordLogin from "@/views/PasswordLogin.vue";
import UserRegister from "@/views/UserRegister.vue";
import ForgetPassword from "@/views/ForgetPassword.vue";
import UserDetail from '@/views/UserDetail.vue';
import UserMoments from "@/article/UserMoments.vue";
import UserPublish from "@/article/UserPublish.vue";
import UserDetailMoment from "@/article/UserDetailMoment.vue";
import UserPage from "@/views/UserPage.vue";
import ChatView from '@/views/ChatView_2.vue'; // 导入聊天组件
import GroupChat from "@/views/GroupChat_2.vue";

const routes = [
  {
    path: "/",
    redirect: "/login",
  },
  {
    path: "/login",
    name: "Login",
    component: UserLogin,
  },
  {
    path: "/password-login",
    component: PasswordLogin,
  },
  {
    path: "/register",
    component: UserRegister,
  },
  {
    path: '/forgot-password',
    name: 'ForgetPassword',
    component: ForgetPassword
  },
  {
    path: '/user-moment',
    name: 'UserPage',
    component: UserPage
  },
  {
    path: "/user",
    component: UserLayout, // 使用布局组件
    children: [
      {
        path: "dashboard",
        component: UserDashboard,
      },
      {
        path: "userinfo",
        component: UserInfo,
        children: [
          {
            path: "userlist",
            component: UserList,
          },
          {
            path: ":userId",
            component: UserDetail,
          }
        ],
      },
      {
        path: "bigdatauser",
        component: BigdataUser,
        children: [
          {
            path: ":userId",
            component: UserDetail, // 共用用户详情组件
          }
        ],
      },
      {
        path: 'chat/:id', // 聊天路由
        name: 'Chat',
        component: ChatView
      },
      {
        path: 'chat/:id', // 群聊天路由
        name: 'GroupChat',
        component: GroupChat
      },
    ],
  },
  {
    path: "/publish",
    name: "UserPublish",
    component: UserPublish,
    meta: { requiresAuth: true },
  },
  {
    path: "/moments",
    name: "UserMoments",
    component: UserMoments,
    meta: { requiresAuth: true },
  },
  {
    path: "/moment/:momentId",
    name: "UserDetailMoment",
    component: UserDetailMoment,
    meta: { requiresAuth: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 全局前置守卫
router.beforeEach((to, from, next) => {
  const isLoggedIn = localStorage.getItem("token");
  if (to.meta.requiresAuth && !isLoggedIn) {
    next("/login");
  } else {
    next();
  }
});

export default router;