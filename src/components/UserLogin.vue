<template>
  <div class="login-wrapper">
    <div class="user-login-container">
      <!-- 根据登录类型显示不同的标题 -->
      <h1>{{ isPasswordLogin ? '密码登录' : '用户登录' }}</h1>
      <form @submit.prevent="handleLogin">
        <!-- 登录方式选择，当不是密码登录时显示 -->
        <div v-if="!isPasswordLogin" class="login-type">
          <label>
            <input
              type="radio"
              v-model="loginType"
              value="phone"
              :disabled="isPasswordLogin"
            /> 短信登录
          </label>
          <label>
            <input
              type="radio"
              v-model="loginType"
              value="email"
              :disabled="isPasswordLogin"
            /> 邮箱登录
          </label>
        </div>

        <!-- 手机号登录，当不是密码登录且选择短信登录时显示 -->
        <div v-if="loginType === 'phone' && !isPasswordLogin" class="input-group">
          <input
            type="text"
            v-model="phone"
            placeholder="请输入手机号"
            required
          />
        </div>

        <!-- 邮箱登录，当不是密码登录且选择邮箱登录时显示 -->
        <div v-else-if="loginType === 'email' && !isPasswordLogin" class="input-group">
          <input
            type="email"
            v-model="email"
            placeholder="请输入邮箱"
            required
          />
        </div>

        <!-- 验证码输入，当不是密码登录时显示 -->
        <div v-if="!isPasswordLogin" class="input-group code-group">
          <input
            type="text"
            v-model="code"
            placeholder="请输入验证码"
            required
          />
          <button
            type="button"
            @click="sendCode"
            class="code-button"
            :disabled="isCodeButtonDisabled"
          >
            {{ codeButtonText }}
          </button>
        </div>

        <!-- 密码登录链接，当不是密码登录时显示 -->
        <div v-if="!isPasswordLogin" class="switch-links">
          <span class="switch-login-link" @click="togglePasswordLogin">密码登录</span>
          <span class="register-link" @click="goToRegisterPage">注册新用户</span>
        </div>

        <!-- 密码登录表单 -->
        <div v-if="isPasswordLogin" class="password-login-form">
          <div class="input-group">
            <input
              type="text"
              v-model="phone"
              placeholder="请输入用户名/手机号/邮箱"
              required
              @input="checkphone"
            />
            <span
              v-if="isPasswordLogin && phoneCheckResult!== null"
              :class="{ 'check-icon': true, 'check-icon-valid': phoneCheckResult, 'check-icon-invalid':!phoneCheckResult }"
            >
              {{ phoneCheckResult? '✔' : '✖' }}
            </span>
            <p v-if="isPasswordLogin && phoneCheckResult === false" class="error-message">用户不存在</p>
          </div>
          <div class="input-group">
            <input
              type="password"
              v-model="password"
              placeholder="请输入密码"
              required
            />
          </div>
          <!-- 验证码登录和找回密码链接，当是密码登录时显示 -->
          <div v-if="isPasswordLogin" class="switch-links">
            <span class="switch-login-link" @click="togglePasswordLogin">验证码登录</span>
            <span class="forgot-password-link" @click="goToForgotPasswordPage">找回密码</span>
          </div>
        </div>

        <!-- 登录按钮 -->
        <button type="submit" class="login-button">
          {{ isPasswordLogin ? "密码登录" : "登录" }}
        </button>
      </form>

      <!-- 显示登录结果 -->
      <div v-if="loginResult" class="login-result">
        <p v-if="loginResult.success">登录成功！</p>
        <p v-else>登录失败：{{ loginResult.message }}</p>
      </div>
    </div>

    <!-- 验证码弹窗 -->
    <div v-if="showCodeModal" class="modal-overlay">
      <div class="modal-content">
        <h3>验证码已发送</h3>
        <p>您的验证码是：<strong>{{ generatedCode }}</strong></p>
        <button @click="fillCodeAndCloseModal">填充验证码并关闭</button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { API_CONFIG } from '@/config/config';

export default {
  name: "UserLogin",
  data() {
    return {
      loginType: "phone", // 登录方式：phone 或 email
      phone: "", // 手机号
      email: "", // 邮箱
      code: "", // 验证码
      username: "", // 用户名/手机号/邮箱（用于密码登录）
      password: "", // 密码（用于密码登录）
      loginResult: null, // 登录结果
      generatedCode: "", // 从后端获取的验证码
      showCodeModal: false, // 是否显示验证码弹窗
      isCodeButtonDisabled: false, // 获取验证码按钮是否禁用
      codeButtonText: "获取验证码", // 获取验证码按钮文本
      countdown: 0, // 倒计时时间
      isPasswordLogin: false, // 是否使用密码登录
      phoneCheckResult: null // 用户名检查结果
    };
  },
  methods: {
    // 发送验证码
    async sendCode() {
      if (this.loginType === "phone" && !this.phone) {
        alert("请输入手机号");
        return;
      }
      if (this.loginType === "email" && !this.email) {
        alert("请输入邮箱");
        return;
      }

      try {
        const phone = this.loginType === "phone"? this.phone : this.email;

        // 调用后端接口获取验证码
        const response = await axios.post(`${API_CONFIG.BASE_URL}/api/send-code`, {
          phone
        });

        // 从后端获取验证码
        this.generatedCode = response.data.code;

        // 显示验证码弹窗
        this.showCodeModal = true;

        // 启动倒计时
        this.startCountdown();
      } catch (error) {
        console.error("验证码请求失败：", error.response?.data);
        alert("验证码发送失败");
      }
    },

    // 启动倒计时
    startCountdown() {
      this.isCodeButtonDisabled = true; // 禁用按钮
      this.countdown = 60; // 设置倒计时时间
      const timer = setInterval(() => {
        this.countdown--;
        if (this.countdown <= 0) {
          clearInterval(timer);
          this.isCodeButtonDisabled = false; // 恢复按钮
          this.codeButtonText = "获取验证码"; // 恢复按钮文本
        } else {
          this.codeButtonText = `${this.countdown}s后重新获取`; // 更新按钮文本
        }
      }, 1000);
    },

    // 填充验证码并关闭弹窗
    fillCodeAndCloseModal() {
      this.code = this.generatedCode; // 将验证码填充到输入框
      this.showCodeModal = false; // 关闭弹窗
    },

    // 处理登录
    async handleLogin() {
      if (this.isPasswordLogin) {
        // 密码登录逻辑
        await this.handlePasswordLogin();
      } else {
        // 验证码登录逻辑
        await this.handleCodeLogin();
      }
    },

    // 处理验证码登录
    async handleCodeLogin() {
      if (!this.code) {
        alert("请输入验证码");
        return;
      }

      try {
        const phone = this.loginType === "phone"? this.phone : this.email;
        const password = this.code;

        // 调用后端登录接口
        const response = await axios.post(
          `${API_CONFIG.BASE_URL}/api/login`,
          {
            phone,
            password
          },
          {
            headers: {
              "Content-Type": "application/json"
            }
          }
        );

        // 登录成功
        this.loginResult = {
          success: true,
          message: "登录成功！",
          data: response.data
        };
          console.log("Data = ", response.data)
        // 存储用户信息和 Token 到 Vuex
        this.$store.dispatch("login", {
          user: response.data.user,
          token: response.data.access_token
        });

        // 跳转到用户页面
        this.$router.push("/user/dashboard");
      } catch (error) {
        // 登录失败
        this.loginResult = {
          success: false,
          message: error.response?.data?.detail || "登录失败"
        };
      }
    },

    // 处理密码登录
    async handlePasswordLogin() {
      if (!this.phone || !this.password) {
        alert("请输入用户名和密码");
        return;
      }

      try {
        // 先检查用户名是否存在
        const checkResponse = await axios.post(
          `${API_CONFIG.BASE_URL}/api/check-user`,
          {
            phone: this.phone
          },
          {
            headers: {
              "Content-Type": "application/json"
            }
          }
        );
        this.phoneCheckResult = checkResponse.data.exists;
        if (!this.phoneCheckResult) {
          return;
        }

        // 调用后端密码登录接口
        const response = await axios.post(
          `${API_CONFIG.BASE_URL}/api/password-login`,
          {
            phone: this.phone,
            password: this.password
          },
          {
            headers: {
              "Content-Type": "application/json"
            }
          }
        );

        // 登录成功
        this.loginResult = {
          success: true,
          message: "登录成功！",
          data: response.data
        };

        // 存储用户信息和 Token 到 Vuex
        this.$store.dispatch("login", {
          user: response.data.user,
          token: response.data.access_token
        });

        // 跳转到用户页面
        this.$router.push("/user/dashboard");
      } catch (error) {
        // 登录失败
        this.loginResult = {
          success: false,
          message: error.response?.data?.detail || "登录失败"
        };
      }
    },

    // 切换密码登录
    togglePasswordLogin() {
      this.isPasswordLogin = !this.isPasswordLogin;
      // 清空验证码登录的输入框
      if (this.isPasswordLogin) {
        this.phone = "";
        this.email = "";
        this.code = "";
        this.phoneCheckResult = null;
      } else {
        this.phone = "";
        this.password = "";
      }
    },

    // 跳转到注册页面
    goToRegisterPage() {
      this.$router.push("/register");
    },

    // 跳转到找回密码页面
    goToForgotPasswordPage() {
      this.$router.push("/forgot-password");
    },

    // 检查用户名是否存在
    async checkphone() {
      if (this.isPasswordLogin && this.phone) {
        try {
          const checkResponse = await axios.post(
            `${API_CONFIG.BASE_URL}/api/check-user`,
            {
              phone: this.phone
            },
            {
              headers: {
                "Content-Type": "application/json"
              }
            }
          );
          this.phoneCheckResult = checkResponse.data.exists;
        } catch (error) {
          console.error("检查用户存在性失败：", error.response?.data);
          this.phoneCheckResult = null;
        }
      } else {
        this.phoneCheckResult = null;
      }
    }
  }
};
</script>

<style scoped>
/* 样式保持不变 */
.login-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f5f5;
}

.user-login-container {
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

.login-type {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}

.login-type label {
  margin: 0 10px;
  font-size: 16px;
}

.input-group {
  margin-bottom: 15px;
  position: relative;
}

.input-group input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
  font-size: 16px;
}

.check-icon {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 20px;
}

.check-icon-valid {
  color: green;
}

.check-icon-invalid {
  color: red;
}

.error-message {
  color: red;
  font-size: 12px;
  margin-top: 5px;
}

.code-group {
  display: flex;
  align-items: center;
}

.code-group input {
  flex: 1;
  margin-right: 10px;
}

.code-button {
  padding: 10px 15px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
}

.code-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.code-button:hover:not(:disabled) {
  background-color: #369f6e;
}

.password-login-form {
  margin-bottom: 15px;
}

.switch-links {
  display: flex;
  justify-content: space-between;
  margin-top: 5px;
  font-size: 12px; /* 小字体显示 */
}

.switch-login-link,
.register-link,
.forgot-password-link {
  color: #42b983;
  cursor: pointer;
}

.switch-login-link:hover,
.register-link:hover,
.forgot-password-link:hover {
  text-decoration: underline;
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

.login-result {
  margin-top: 20px;
  text-align: center;
  font-size: 16px;
  color: #333;
}

/* 弹窗样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-content {
  background-color: white;
  padding: 20px;
  border-radius: 10px;
  text-align: center;
}

.modal-content h3 {
  margin-bottom: 10px;
}

.modal-content button {
  margin-top: 10px;
  padding: 10px 20px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.modal-content button:hover {
  background-color: #369f6e;
}
</style> 