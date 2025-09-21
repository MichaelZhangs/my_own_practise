<template>
    <div class="password-login">
      <h1>密码登录</h1>
      <form @submit.prevent="handlePasswordLogin">
        <div class="input-group">
          <input
            type="text"
            v-model="phone"
            placeholder="请输入用户名/手机号/邮箱"
            required
          />
        </div>
        <div class="input-group">
          <input
            type="password"
            v-model="password"
            placeholder="请输入密码"
            required
          />
        </div>
        <button type="submit" class="login-button">登录</button>
      </form>
    </div>
  </template>
  
  <script>
  import axios from "axios";
  import { API_CONFIG } from '@/config/config';

  export default {
    name: "PasswordLogin",
    data() {
      return {
        phone: this.$route.query.phone || "", // 从路由参数中获取用户名
        password: "",
      };
    },
    methods: {
      async handlePasswordLogin() {
        try {
          const response = await axios.post(`${API_CONFIG.BASE_URL}/api/password-login`, {
            phone: this.phone,
            password: this.password,
          });
  
          // 登录成功
           this.$store.dispatch("login", {
            user: response.data.user,
            token: response.data.access_token,
          });
          
        const { user, token } = response.data;

        // 更新 Vuex 状态
        this.$store.dispatch("login", { user, token });

          // 跳转到用户页面
          this.$router.push("/user/dashboard");
        } catch (error) {
          if (error.response?.status === 400) {
            // 密码错误，跳转到重置密码页面
            this.$router.push({
              path: "/reset-password",
              query: { phone: this.phone },
            });
          } else {
            console.error("登录失败", error);
          }
        }
      },
    },
  };
  </script>
  
  <style scoped>
  .password-login {
    max-width: 400px;
    margin: 0 auto;
    padding: 20px;
    background-color: white;
    border-radius: 10px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  }
  
  h1 {
    text-align: center;
    color: #333;
    margin-bottom: 20px;
  }
  
  .input-group {
    margin-bottom: 15px;
  }
  
  .input-group input {
    width: 100%;
    padding: 10px;
    border: 1px solid #ccc;
    border-radius: 5px;
    font-size: 16px;
  }
  
  .login-button {
    width: 100%;
    padding: 10px;
    background-color: #42b983;
    color: white;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    font-size: 16px;
  }
  
  .login-button:hover {
    background-color: #369f6e;
  }
  </style>