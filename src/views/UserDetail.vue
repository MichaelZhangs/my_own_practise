<template>
  <div class="user-detail-page">
    <h1 class="page-title">用户详情</h1>
    <div class="user-container">
      <!-- 可编辑头像 -->
      <div class="avatar-wrapper">
        <label class="avatar-upload">
          <input 
            type="file" 
            accept="image/*" 
            @change="handleAvatarUpload" 
            hidden
          />
          <img 
            :src="editableUser.photo ? `http://127.0.0.1:8000${editableUser.photo}?t=${Date.now()}` : defaultAvatar" 
            alt="用户头像" 
            class="user-avatar"
          />
          <span class="edit-tip">点击更换头像</span>
        </label>
      </div>

      <!-- 用户信息编辑 -->
      <div class="info-section">
        <div class="info-item">
          <label>姓名：</label>
          <input v-model="editableUser.username" class="short-input" />
        </div>
        
        <div class="info-item">
          <label>性别：</label>
          <select v-model="editableUser.sex">
            <option value="male">male</option>
            <option value="female">female</option>
          </select>
        </div>

        <div class="info-item">
          <label>手机：</label>
          <input
            v-model="editableUser.phone"
            :readonly="!isPhoneEditable"
            class="short-input"
            @dblclick="enablePhoneEdit"
            @blur="isPhoneEditable = false"
          />
          <span v-if="!isPhoneEditable" class="edit-hint">(双击编辑)</span>
        </div>

        <div class="info-item">
          <label>邮箱：</label>
          <input v-model="editableUser.email" class="short-input" />
        </div>

        <div class="info-item">
          <label>描述：</label>
          <input v-model="editableUser.description" class="short-input" />
        </div>

        <!-- 二维码展示 -->
        <div class="info-item">
          <label class="qr-label">我的二维码：</label>
          <div class="qr-wrapper" @click="generateQRWithAvatar">
            <img 
              :src="editableUser.qrcode ? `http://127.0.0.1:8000${editableUser.qrcode}?t=${Date.now()}` : defaultQR" 
              alt="个人二维码" 
              class="wechat-qr"
            />
          </div>
        </div>
      </div>

      <button class="save-btn" @click="saveUserInfo">保存修改</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router'; // 引入 useRouter
import axios from 'axios';
import QRCode from 'qrcode';
import defaultAvatar from '@/assets/default-avatar.png';
import defaultQR from '@/assets/logo.png';
import { API_CONFIG } from '@/config/config';

const store = useStore();
const router = useRouter(); // 获取路由实例

// 响应式数据
const editableUser = ref({
  ...store.state.user,
  description: store.state.user.description || ''
});
const qrcodeUrl = ref(defaultQR);
const isPhoneEditable = ref(false);

// 启用手机号编辑
const enablePhoneEdit = async () => {
  isPhoneEditable.value = true;
  document.querySelector('.short-input[readonly]')?.focus();
};

// 头像上传处理
const handleAvatarUpload = async (event) => {
  const file = event.target.files?.[0];
  if (!file || !file.type.startsWith('image/')) return;

  try {
    // 将文件转换为 Base64
    const reader = new FileReader();
    reader.readAsDataURL(file);

    reader.onload = async () => {
      const base64Image = reader.result; // 获取 Base64 编码的图片数据

      // 调用后端上传头像接口
      const response = await axios.post(`${API_CONFIG.BASE_URL}/user/upload-avatar`, {
        phone: editableUser.value.phone,
        photo: base64Image
      });

      if (response.data.avatar_url) {
        // 更新本地数据（使用相对路径）
        editableUser.value.photo = `${response.data.avatar_url}?t=${Date.now()}`;

        // 更新 Vuex 状态
        await store.dispatch('updateUser', {
          ...editableUser.value,
          photo: response.data.avatar_url
        });

        // 头像上传成功后，强制更新二维码
        await generateQRWithAvatar();
      }
    };

    reader.onerror = (error) => {
      console.error('文件读取失败:', error);
      alert('文件读取失败，请重试');
    };
  } catch (error) {
    console.error('头像上传失败:', error);
    alert('头像上传失败，请重试');
  }
};

// 生成带头像的二维码
const generateQRWithAvatar = async () => {
  try {
    const userData = {
      name: editableUser.value.username || "未设置",
      phone: editableUser.value.phone || "未设置",
      email: editableUser.value.email || "未设置",
      description: editableUser.value.description || "未设置"
    };
    console.log("生成二维码的数据： ", userData);

    const canvas = document.createElement('canvas');
    await QRCode.toCanvas(canvas, JSON.stringify(userData), {
      width: 200,
      margin: 2,
      color: {
        dark: '#07c160',
        light: '#ffffff'
      },
      errorCorrectionLevel: 'H'
    });

    console.log("二维码生成成功");
    const ctx = canvas.getContext('2d');
    const avatarImg = new Image();

    // 处理头像路径
    let avatarUrl = defaultAvatar; // 默认头像
    if (editableUser.value.photo) {
      avatarUrl = `${API_CONFIG.BASE_URL}${editableUser.value.photo}`;
    }

    avatarImg.src = avatarUrl;
    avatarImg.crossOrigin = 'anonymous';

    console.log("头像图片路径:", avatarImg.src);

    await new Promise((resolve) => {
      avatarImg.onload = () => {
        console.log("头像图片加载成功");
        resolve();
      };
      avatarImg.onerror = (error) => {
        console.error("头像图片加载失败:", error);
        avatarImg.src = defaultAvatar;
        resolve();
      };
    });

    ctx.beginPath();
    ctx.arc(100, 100, 25, 0, Math.PI * 2);
    ctx.clip();
    ctx.drawImage(avatarImg, 75, 75, 50, 50);

    const qrDataUrl = canvas.toDataURL();

    // 保存二维码到后端
    const response = await axios.post(`${API_CONFIG.BASE_URL}/user/save-qrcode`, {
      phone: editableUser.value.phone,
      qrcode: qrDataUrl
    });

    if (response.data.qrcode_url) {
      editableUser.value.qrcode = response.data.qrcode_url;
      qrcodeUrl.value = `${API_CONFIG.BASE_URL}${response.data.qrcode_url}?t=${Date.now()}`;

      await store.dispatch('updateUser', {
        ...editableUser.value,
        qrcode: response.data.qrcode_url
      });
    }
  } catch (error) {
    console.error('二维码生成失败:', error);
    alert('二维码生成失败，请重试');
  }
};

// 获取用户信息
const fetchUserInfo = async () => {
  try {
    const response = await axios.get(`${API_CONFIG.BASE_URL}/user/info`, {
      params: {
        id: editableUser.value.id
      }
    });
    
    if (response.data) {
      editableUser.value = {
        username: response.data.username || "",
        phone: response.data.phone || "",
        email: response.data.email || "",
        sex: response.data.sex || "male",
        description: response.data.description || "",
        photo: response.data.photo || "",
        qrcode: response.data.qrcode || ""
      };

      await store.dispatch('updateUser', response.data);
    }
  } catch (error) {
    console.error('获取用户信息失败:', error);
    alert('获取用户信息失败，请重试');
  }
};

// 组件挂载时自动获取用户信息
onMounted(async () => {
  await fetchUserInfo();
});

// 保存用户信息
const saveUserInfo = async () => {
  try {
    const requestData = {
      username: editableUser.value.username,
      email: editableUser.value.email || "",
      sex: editableUser.value.sex,
      description: editableUser.value.description || "",
      phone: editableUser.value.phone,
      qrcode: editableUser.value.qrcode
    };

    const response = await axios.put(`${API_CONFIG.BASE_URL}/user/info`, requestData);
    console.log("response: ", response.status);

    if (response.status === 200) {
      editableUser.value = {
        ...editableUser.value,
        ...requestData
      };

      await store.dispatch('updateUser', editableUser.value);

      // 保存成功后跳转到用户页面
     router.push('/user');
    }
  } catch (error) {
    console.error('保存失败:', error);
    const errorMsg = error.response?.data?.detail || '保存失败，请检查网络后重试';
    alert(`保存失败: ${errorMsg}`);
  }
};
</script>

<style scoped>
/* 基础布局 */
.user-detail-page {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
  font-family: 'Helvetica Neue', Arial, sans-serif;
}

.page-title {
  text-align: center;
  font-size: 1.5rem;
  color: #333;
  margin-bottom: 2rem;
}

.user-container {
  background: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* 头像样式 */
.avatar-wrapper {
  text-align: center;
  margin-bottom: 1.5rem;
}

.user-avatar {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: 3px solid #07c160;
  cursor: pointer;
  transition: transform 0.3s ease;
}

.user-avatar:hover {
  transform: scale(1.05);
}

/* 二维码标签特殊样式 */
.qr-label {
  margin-top: 5px; /* 保持垂直对齐 */
}

.edit-tip {
  display: block;
  color: #666;
  font-size: 0.8rem;
  margin-top: 0.5rem;
}

/* 手机号编辑提示 */
.edit-hint {
  color: #999;
  font-size: 0.8rem;
  margin-left: 10px;
}

/* 手机号输入框只读状态 */
input:read-only {
  background-color: #f5f5f5;
  cursor: not-allowed;
  border-color: #eee;
}

/* 信息项样式 */
.info-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.info-item label {
  flex: 0 0 100px;
  text-align: left; /* 改为左对齐 */
  color: #666;
  font-size: 0.9rem;
  margin-right: 15px;
}

/* 输入控件样式 */
.short-input, select {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  max-width: 300px;
  font-size: 0.9rem;
}

select {
  background: white;
  cursor: pointer;
}

/* 二维码区域 */
.qr-wrapper {
  flex: 1;
  cursor: pointer;
}

.wechat-qr {
  width: 160px;
  height: 160px;
  border: 3px solid #07c160;
  border-radius: 8px;
  padding: 5px;
  background: white;
  transition: transform 0.3s ease;
}

.wechat-qr:hover {
  transform: scale(1.05);
}

/* 保存按钮 */
.save-btn {
  display: block;
  width: 200px;
  padding: 0.8rem;
  margin: 2rem auto 0;
  background: #07c160;
  color: white;
  border: none;
  border-radius: 25px;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.3s ease;
}

.save-btn:hover {
  background: #05964d;
}

/* 响应式设计 */
@media (max-width: 480px) {
  .user-container {
    padding: 1rem;
  }

  .info-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .info-item label {
    text-align: left;
    flex: none;
  }

  .short-input, select {
    max-width: 100%;
    width: 100%;
  }

  .wechat-qr {
    width: 140px;
    height: 140px;
  }
}
</style>