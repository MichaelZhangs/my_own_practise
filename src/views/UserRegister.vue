<template>
  <div class="register-wrapper">
    <div class="register-container">
      <h1>用户注册</h1>
      <form @submit.prevent="handleRegister">
        <div class="input-group">
          <input
            type="text"
            v-model="username"
            placeholder="请输入用户名"
            required
          />
        </div>
        <div class="input-group">
          <input
            type="text"
            v-model="phone"
            placeholder="请输入电话号码"
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
        <div class="input-group">
          <input
            type="password"
            v-model="confirmPassword"
            placeholder="请再次输入密码"
            required
          />
          <p v-if="password!== confirmPassword && confirmPassword" class="error-message">两次输入的密码不一致</p>
        </div>
        <button type="submit" class="register-button" :disabled="password!== confirmPassword">注册</button>
      </form>
      <div v-if="registerResult" class="register-result">
        <p v-if="registerResult.success">注册成功！请登录。</p>
        <p v-else>注册失败：{{ registerResult.message }}</p>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { API_CONFIG } from '@/config/config';

export default {
  name: "UserRegister",
  data() {
    return {
      username: "",
      phone: "",
      password: "",
      confirmPassword: "",
      registerResult: null
    };
  },
  methods: {
  async handleRegister() {
    if (this.password !== this.confirmPassword) {
      alert("两次输入的密码不一致");
      return;
    }
    try {
     const response =   await axios.post(
        `${API_CONFIG.BASE_URL}/api/register`,
        {
          username: this.username,
          phone: this.phone,
          password: this.password,
        },
        {
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

              // 存储用户信息和 Token 到 Vuex
      await this.$store.dispatch("login", {
          user: response.data.user,
          token: response.data.access_token  // 兼容两种字段名
        });
            // 强制刷新Vuex状态
   
        console.log("当前localStorage:", localStorage.getItem("token"));
      // 注册成功，跳转到 user 页面并传递用户信息
  
      this.$router.push({
        path: "/user",
        query: {
          username: this.username,
          phone: this.phone,
        },
      }).catch(err => {
      console.error("路由跳转失败:", err);
    });
    } catch (error) {
      this.registerResult = {
        success: false,
        message: error.response?.data?.detail || "注册失败",
      };
    }
  },
},
};
</script>

<style scoped>
.register-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f5f5;
}

.register-container {
  max-width: 400px;
  width: 100%;
  padding: 30px;
  border-radius: 10px;
  background-color: white;
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

.error-message {
  color: red;
  font-size: 12px;
  margin-top: 5px;
}

.register-button {
  width: 100%;
  padding: 10px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 16px;
}

.register-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.register-button:hover:not(:disabled) {
  background-color: #369f6e;
}

.register-result {
  margin-top: 20px;
  text-align: center;
  font-size: 16px;
  color: #333;
}
</style>