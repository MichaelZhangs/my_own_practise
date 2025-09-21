<template>
  <div class="forgot-password-container">
    <h1>找回密码</h1>
    <form @submit.prevent="handleSubmit">
      <div class="input-group">
        <input
          type="text"
          v-model="identifier"
          placeholder="请输入电话号码或邮箱"
          required
        />
      </div>
      <div class="input-group">
        <input
          :type="showNewPassword? 'text' : 'password'"
          v-model="newPassword"
          placeholder="请输入新密码"
          required
        />
        <i
          class="toggle-password"
          :class="{ 'fa-eye':!showNewPassword, 'fa-eye-slash': showNewPassword }"
          @click="showNewPassword = !showNewPassword"
        ></i>
      </div>
      <div class="input-group">
        <input
          :type="showConfirmPassword? 'text' : 'password'"
          v-model="confirmPassword"
          placeholder="请再次输入新密码"
          required
        />
        <i
          class="toggle-password"
          :class="{ 'fa-eye':!showConfirmPassword, 'fa-eye-slash': showConfirmPassword }"
          @click="showConfirmPassword = !showConfirmPassword"
        ></i>
      </div>
      <div v-if="passwordMismatch && confirmPassword" class="error-message">密码不一致</div>
      <div class="input-group code-group">
        <input
          type="text"
          v-model="verificationCode"
          placeholder="请输入验证码"
          required
        />
        <button
          type="button"
          @click="sendVerificationCode"
          class="code-button"
          :disabled="isCodeButtonDisabled"
        >
          {{ codeButtonText }}
        </button>
      </div>
      <button type="submit" class="submit-button">提交</button>
    </form>
    <div v-if="resultMessage" class="result-message">
      <p :class="{ success: resultSuccess, error:!resultSuccess }">{{ resultMessage }}</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { API_CONFIG } from '@/config/config';

export default {
  name: 'ForgetPassword',
  data() {
    return {
      identifier: '',
      newPassword: '',
      confirmPassword: '',
      verificationCode: '',
      isCodeButtonDisabled: false,
      codeButtonText: '获取验证码',
      countdown: 0,
      resultMessage: '',
      resultSuccess: false,
      passwordMismatch: false,
      showNewPassword: false,
      showConfirmPassword: false,
      generatedCode: null
    };
  },
  watch: {
    confirmPassword(newVal) {
      if (this.newPassword) {
        this.passwordMismatch = newVal!== this.newPassword;
      }
    }
  },
  methods: {
    async sendVerificationCode() {
      if (!this.identifier) {
        alert('请输入电话号码或邮箱');
        return;
      }
      if (this.passwordMismatch && this.confirmPassword) {
        return;
      }
      try {
        const response = await axios.post(`${API_CONFIG.BASE_URL}/api/send-verification-code`, {
          identifier: this.identifier,
          newPassword: this.newPassword
        });
        this.generatedCode = response.data.code;
        this.verificationCode = this.generatedCode; // 自动回填验证码
        this.startCountdown();
      } catch (error) {
        console.error('发送验证码失败:', error);
        alert('发送验证码失败，请稍后重试');
      }
    },
    startCountdown() {
      this.isCodeButtonDisabled = true;
      this.countdown = 60;
      this.codeButtonText = `${this.countdown}s 后重新获取`;
      const timer = setInterval(() => {
        this.countdown--;
        if (this.countdown <= 0) {
          clearInterval(timer);
          this.isCodeButtonDisabled = false;
          this.codeButtonText = '获取验证码';
        } else {
          this.codeButtonText = `${this.countdown}s 后重新获取`;
        }
      }, 1000);
    },
    async handleSubmit() {
      if (!this.identifier || !this.newPassword || !this.confirmPassword || !this.verificationCode) {
        alert('请填写所有必填字段');
        return;
      }
      if (this.passwordMismatch && this.confirmPassword) {
        return;
      }
      try {
        const response = await axios.post(`${API_CONFIG.BASE_URL}/api/reset-password`, {
          identifier: this.identifier,
          verificationCode: this.verificationCode,
          newPassword: this.newPassword
        });
        console.log("response : ", response);
        this.resultMessage = '密码重置成功，请使用新密码登录';
        this.resultSuccess = true;
      } catch (error) {
        console.error('密码重置失败:', error);
        this.resultMessage = '密码重置失败，请重试';
        this.resultSuccess = false;
      }
    }
  }
};
</script>

<style scoped>
.forgot-password-container {
  max-width: 400px;
  margin: 0 auto;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 5px;
  background-color: #f9f9f9;
}

h1 {
  text-align: center;
  margin-bottom: 20px;
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
}

.toggle-password {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
  color: #007bff;
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
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.code-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.submit-button {
  width: 100%;
  padding: 10px;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.submit-button:hover {
  background-color: #218838;
}

.result-message {
  margin-top: 15px;
  text-align: center;
}

.success {
  color: green;
}

.error {
  color: red;
}

.error-message {
  color: red;
  margin-bottom: 10px;
}
</style>

<style>
/* 引入 Font Awesome 图标库 */
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css');
</style>