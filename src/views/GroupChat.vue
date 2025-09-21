<template>
  <div class="chat-view">
    <div class="chat-header">
      <div class="back-button" @click="goBack">
        <i class="fa fa-arrow-left" aria-hidden="true"></i>
      </div>
      <div class="chat-title">{{ displayGroupName }}</div>
      <div class="chat-avatar" @click="showGroupInfo = true">
        <div class="group-avatar">
          <div 
            v-for="(avatarUrl, idx) in groupAvatarUrls" 
            :key="idx"
            class="group-avatar-member"
            :style="getAvatarPosition(idx)"
          >
            <img 
              :src="avatarUrl" 
              alt="成员头像"
              onerror="this.src='@/assets/default-avatar.png'"
            />
          </div>
        </div>
      </div>
    </div>
    
    <div class="chat-messages" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-chat">
        开始和 {{ displayGroupName }} 聊天吧
      </div>
      
      <div 
        v-for="(msg, index) in messages || []" 
        :key="msg.id || index" 
        :class="['message-item', msg.fromMe ? 'from-me' : 'from-other']"
      >
        <div class="message-avatar">
          <img 
            :src="getSenderAvatar(msg)" 
            alt="头像" 
            class="avatar-sm" 
            onerror="this.src='@/assets/default-avatar.png'"
          />
        </div>
        
        <div class="message-content">
          <div class="message-sender" v-if="!msg.fromMe">{{ findSenderName(msg) }}</div>
          
          <div class="message-bubble" v-if="msg.text" v-html="formatMessage(msg.text)"></div>
          
          <div class="message-media" v-if="msg.media && msg.media.length > 0">
            <div v-for="(item, i) in msg.media" :key="i">
              <img v-if="item.type === 'image'" :src="getFullUrl(item.url)" alt="图片消息" />
              <video v-if="item.type === 'video'" controls>
                <source :src="getFullUrl(item.url)" type="video/mp4">
                您的浏览器不支持视频播放
              </video>
              <a v-if="item.type === 'file' || item.type === 'application'" 
                :href="getFullUrl(item.url)" 
                target="_blank"
                class="file-message"
                :class="{'from-me': msg.fromMe, 'from-other': !msg.fromMe}">
                <div class="file-icon">
                  <i :class="getFileIcon(item)"></i>
                </div>
                <div class="file-info">
                  <div class="file-name">{{ item.original_name || getFileName(item.url) }}</div>
                  <div class="file-meta">
                    <span class="file-type">{{ getFileIcon(item) }}</span>
                    <span class="file-size">{{ formatFileSize(item.size) }}</span>
                  </div>
                </div>
                <div class="file-download">
                  <i class="fa fa-download"></i>
                </div>
              </a>
            </div>
          </div>
          
          <div class="message-time">{{ formatTime(msg.time) }}</div>
        </div>
      </div>
    </div>
    
    <div class="chat-input-area">
      <div class="connection-status" v-if="!isConnected">
        <i class="fa fa-exclamation-triangle" aria-hidden="true"></i> 未连接
      </div>
      
      <div class="media-toolbar">
        <div class="media-buttons">
          <div class="tooltip-container">
            <label class="media-button">
              <i class="fa fa-video-camera" aria-hidden="true"></i>
              <input type="file" accept="video/*" @change="handleFileUpload" ref="videoInput" />
            </label>
            <span class="tooltip">视频</span>
          </div>
          <div class="tooltip-container">
            <label class="media-button">
              <i class="fa fa-file" aria-hidden="true"></i>
              <input type="file" @change="handleFileUpload" ref="fileInput" />
            </label>
            <span class="tooltip">文件</span>
          </div>
        </div>
      </div>

      <div class="input-wrapper">
        <div class="emoji-btn" @click="toggleEmojiPicker">
          <i class="fa-regular fa-face-smile"></i>
        </div>
        
        <div class="upload-progress" v-if="isUploading">
          <div class="upload-progress-bar" :style="{ width: uploadProgress + '%' }"></div>
        </div>
        
        <input 
          type="text" 
          v-model="inputMessage" 
          placeholder="输入消息..." 
          @keyup.enter="sendMessage"
          :disabled="!isConnected"
          ref="messageInput"
          aria-label="消息输入框"
        />
        
        <button 
          @click="sendMessage" 
          class="send-button"
          :disabled="!isConnected || !inputMessage.trim()"
          :class="{'active': inputMessage.trim()}"
        >
          <i class="fa-solid fa-paper-plane"></i>
        </button>
      </div>
      
      <div v-if="showEmojiPicker" class="emoji-picker">
        <div class="emoji-grid">
          <span
            v-for="(emoji, index) in emojis"
            :key="index"
            class="emoji-item cursor-pointer hover:bg-gray-100 p-1 text-center"
            @click="insertEmoji(emoji)"
          >
            {{ emoji }}
          </span>
        </div>
      </div>
    </div>
        <!-- 群信息组件 -->
    <GroupInfo
      :visible="showGroupInfo"
      :groupInfo="targetGroup"
      @update:visible="showGroupInfo = $event"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useStore } from 'vuex';
import defaultAvatar from '@/assets/default-avatar.png';
import { API_CONFIG } from '@/config/config';
import { ElMessage, ElNotification } from 'element-plus';
import axios from 'axios';
import CryptoUtils from '@/utils/crypto';
import emojis from '@/utils/emojis';
import GroupInfo from '../components/GroupInfo.vue';


export default {
   components: {
    GroupInfo
  },

  setup() {
    const route = useRoute();
    const router = useRouter();
    const store = useStore();
    const messagesContainer = ref(null);
    const targetGroup = ref({});
    const messages = ref([]);
    const inputMessage = ref('');
    const myAvatar = computed(() => {
      const user = store.state.user;
      return user.photo ? `${API_CONFIG.BASE_URL}${user.photo}` : defaultAvatar;
    });
    const socket = ref(null);
    const isConnected = ref(false);
    const reconnecting = ref(false);
    const reconnectTimer = ref(null);
    const myId = computed(() => store.state.user.id);
    const myUser = computed(() => store.state.user);
    const cryptoUtils = new CryptoUtils();
    
    const showEmojiPicker = ref(false);
    const messageInput = ref(null);
    const fileInput = ref(null);
    const uploadProgress = ref(0);
    const isUploading = ref(false);

    // 重连相关变量
    const reconnectAttempts = ref(0);
    const maxReconnectAttempts = 5;
    const connectionTimeout = ref(null);

    // 群成员信息
    const groupMembers = ref([]);
    
    // 加载状态
    const isLoading = ref(true);
    const loadError = ref(null);

    // 计算属性
    const displayGroupName = computed(() => {
      console.log("targetGroup: ", targetGroup)
      return targetGroup.value?.group_name  || 
             '未知群聊';
    });

    const showGroupInfo = ref(false);
    const handleGroupUpdated = () => {
      // 重新加载群信息
      fetchGroupInfo(route.params.id);
    };
    const handleGroupExited = () => {
      // 处理退出群聊后的逻辑
      router.back();
    };
    const groupAvatarUrls = computed(() => {
      if (!targetGroup.value) return [defaultAvatar];
      
      // 优先使用 avatar_members 或 avatarMembers
      const avatarMembers = targetGroup.value.avatar_members || 
                          targetGroup.value.avatarMembers || 
                          [];
      
      // 如果有头像成员列表，直接使用
      if (avatarMembers.length > 0) {
        return avatarMembers
          .slice(0, 9)
          .map(url => getFullUrl(url))
          .filter(Boolean);
      }
      
      // 如果没有头像成员列表，使用成员ID获取头像
      const members = targetGroup.value.members || 
                     targetGroup.value.group_members || 
                     [];
      
      return getFirstMembers(members, 9).map(memberId => getMemberAvatar(memberId));
    });

    const getFullUrl = (path) => {
      if (!path) return defaultAvatar;
      return path.startsWith('http') ? path : `${API_CONFIG.BASE_URL}${path}`;
    };
    
    const getFileName = (url) => {
      if (!url) return '文件';
      const parts = url.split('/');
      return parts[parts.length - 1] || '文件';
    };
    
    const formatTime = (time) => {
      if (!time) return '';
      const date = new Date(time);
      const now = new Date();
      
      if (date.toDateString() === now.toDateString()) {
        return date.toTimeString().substring(0, 5);
      }
      
      const yesterday = new Date();
      yesterday.setDate(now.getDate() - 1);
      if (date.toDateString() === yesterday.toDateString()) {
        return '昨天';
      }
      
      return `${date.getMonth() + 1}/${date.getDate()}`;
    };
    
    const getFileIcon = (item) => {
      if (!item || typeof item !== 'object') return 'fa fa-file-o';
      
      const fileName = item.original_name || '';
      const url = item.url || '';
      const contentType = item.content_type || '';
      
      let ext = '';
      if (fileName.includes('.')) {
        ext = fileName.split('.').pop().toLowerCase();
      } else if (url.includes('.')) {
        ext = url.split('.').pop().toLowerCase();
      }
      
      if (contentType.includes('image')) return 'fa fa-file-image-o';
      if (contentType.includes('video')) return 'fa fa-file-video-o';
      if (contentType.includes('audio')) return 'fa fa-file-audio-o';
      if (contentType.includes('pdf')) return 'fa fa-file-pdf-o';
      if (contentType.includes('word')) return 'fa fa-file-word-o';
      if (contentType.includes('excel') || contentType.includes('spreadsheet')) 
        return 'fa fa-file-excel-o';
      if (contentType.includes('powerpoint') || contentType.includes('presentation')) 
        return 'fa fa-file-powerpoint-o';
      
      const iconMap = {
        doc: 'fa fa-file-word-o',
        docx: 'fa fa-file-word-o',
        xls: 'fa fa-file-excel-o',
        xlsx: 'fa fa-file-excel-o',
        csv: 'fa fa-file-excel-o',
        ppt: 'fa fa-file-powerpoint-o',
        pptx: 'fa fa-file-powerpoint-o',
        txt: 'fa fa-file-text-o',
        zip: 'fa fa-file-archive-o',
        rar: 'fa fa-file-archive-o',
        '7z': 'fa fa-file-archive-o',
        default: 'fa fa-file-o'
      };
      
      return iconMap[ext] || iconMap.default;
    };
    
    const formatFileSize = (bytes) => {
      if (!bytes) return '0 B';
      const units = ['B', 'KB', 'MB', 'GB'];
      let size = bytes;
      let unitIndex = 0;
      
      while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
      }
      
      return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
    };
    
    const formatMessage = (text) => {
      if (!text) return '';
      return text.replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, 
        emoji => `<span class="emoji-inline">${emoji}</span>`);
    };
    
    const toggleEmojiPicker = () => {
      showEmojiPicker.value = !showEmojiPicker.value;
    };
    
    const insertEmoji = (emoji) => {
      if (messageInput.value) {
        const input = messageInput.value;
        const start = input.selectionStart;
        const end = input.selectionEnd;
        
        inputMessage.value = 
          inputMessage.value.substring(0, start) + 
          emoji + 
          inputMessage.value.substring(end);
        
        nextTick(() => {
          if (messageInput.value) {
            messageInput.value.focus();
            messageInput.value.setSelectionRange(start + 1, start + 1);
          }
        });
      }
    };

    // 获取成员头像
    const getMemberAvatar = (memberId) => {
      if (memberId === myId.value) {
        return myAvatar.value;
      }
      const member = groupMembers.value.find(m => m.id === memberId);
      return member?.photo ? getFullUrl(member.photo) : defaultAvatar;
    };

    // 获取前N个成员
    const getFirstMembers = (members, count) => {
      if (!members) return [];
      return members.slice(0, count);
    };

    // 获取头像位置样式
    const getAvatarPosition = (index) => {
      const positions = [
        { top: '0%', left: '0%', width: '50%', height: '50%' },
        { top: '0%', left: '50%', width: '50%', height: '50%' },
        { top: '50%', left: '0%', width: '50%', height: '50%' },
        { top: '50%', left: '50%', width: '50%', height: '50%' },
        { top: '16%', left: '16%', width: '33%', height: '33%' },
        { top: '16%', right: '16%', width: '33%', height: '33%' },
        { bottom: '16%', left: '16%', width: '33%', height: '33%' },
        { bottom: '16%', right: '16%', width: '33%', height: '33%' },
        { top: '33%', left: '33%', width: '33%', height: '33%' }
      ];
      return positions[index] || positions[0];
    };

    // 初始化WebSocket连接
    const initWebSocket = () => {
      console.log("尝试初始化WebSocket连接: ", myId.value, targetGroup.value.group_id);
      
      if (!myId.value || !targetGroup.value.group_id) {
        console.error("无法初始化WebSocket: 缺少用户ID或群ID");
        return;
      }
      console.log("连接群聊天: ", myId.value, targetGroup.value)
      // 确保使用正确的WebSocket URL
      const wsUrl =`ws://${API_CONFIG.URL_CHAT}/ws/group/chat/${targetGroup.value.group_id}/${myId.value}`
      console.log("wsUrl: ", wsUrl)
      // 关闭现有连接
      if (socket.value) {
        socket.value.onclose = null;
        socket.value.onerror = null;
        socket.value.close();
      }
      
      socket.value = new WebSocket(wsUrl);
      
      socket.value.onopen = () => {
        console.log("WebSocket连接成功");
        isConnected.value = true;
        reconnecting.value = false;
        reconnectAttempts.value = 0;
        isLoading.value = false;
        loadError.value = null;
        
        ElNotification({
          title: '连接成功',
          message: `已加入 ${displayGroupName.value}`,
          type: 'success',
          duration: 3000
        });
        
        loadHistoryMessages();
      };
      
      socket.value.onmessage = async (event) => {
        resetConnectionTimeout();

        try {
          const messageData = JSON.parse(event.data);
          let msg;
          
          if (messageData.encrypt_data && messageData.publick_key) {
            msg = await cryptoUtils.decrypt(
              messageData.encrypt_data,
              messageData.publick_key
            );
          } else {
            msg = messageData;
          }
          
          addMessage({
            id: msg.id,
            text: msg.text,
            media: msg.media || [],
            fromId: msg.from_id,
            fromMe: msg.from_id === myId.value,
            time: msg.time,
            from_username: msg.from_username,
            from_photo: msg.from_photo
          });
          
          // 更新最近聊天列表
          updateRecentChat();
        } catch (e) {
          console.error('解析消息失败', e);
          ElMessage.error('接收消息失败');
        }
      };
      
      socket.value.onclose = (event) => {
        console.log("WebSocket连接关闭:", event.code, event.reason);
        isConnected.value = false;
        
        if (!reconnecting.value && !loadError.value) {
          ElNotification({
            title: '连接断开',
            message: '群聊连接已断开，正在尝试重连...',
            type: 'warning',
            duration: 0
          });
          startReconnect();
        }
      };
      
      socket.value.onerror = (errorEvent) => {
        console.error('WebSocket错误', errorEvent);
        isLoading.value = false;
        loadError.value = 'WebSocket连接错误，请稍后重试';
      };
      
      // 设置连接超时
      resetConnectionTimeout();
    };
    
    // 重置连接超时计时器
    const resetConnectionTimeout = () => {
      clearTimeout(connectionTimeout.value);
      connectionTimeout.value = setTimeout(() => {
        if (socket.value && socket.value.readyState !== WebSocket.OPEN) {
          console.log('WebSocket连接超时，尝试重连');
          socket.value.close();
          startReconnect();
        }
      }, 10000); // 10秒超时
    };
    
    // 加载历史消息
const loadHistoryMessages = async () => {
  if (myId.value && targetGroup.value.group_id) {
    try {
      const res = await axios.get(`${API_CONFIG.BASE_URL}/ws/group/chat/history/${myId.value}/${targetGroup.value.group_id}`, {
        headers: { Authorization: `Bearer ${store.state.token}` }
      });
      
      if (res.data && res.data.length) {
        console.log(res.data)
        const formattedMessages = res.data.map(msg => ({
          id: msg.id,
          text: msg.text,
          media: msg.media || [],
          fromId: msg.from_id,
          fromMe: msg.from_id === myId.value,
          from_username: msg.from_username,
          from_photo: msg.from_photo,
          time: msg.time
        }));
        
        messages.value = formattedMessages;
        nextTick(() => {
          if (messagesContainer.value) {
            messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
          }
        });
      }
    } catch (err) {
      console.error('加载历史消息失败', err);
      ElMessage.warning('历史消息加载失败');
    }
  }
};
    
    // 重连逻辑
    const startReconnect = () => {
      if (reconnecting.value || !targetGroup.value.group_id) return;
      
      reconnecting.value = true;
      reconnectAttempts.value++;
      
      const delay = Math.min(
        3000 * Math.pow(2, reconnectAttempts.value - 1), 
        30000 // 最大延迟30秒
      );
      
      console.log(`尝试重连 (${reconnectAttempts.value}/${maxReconnectAttempts})，延迟: ${delay/1000}秒`);
      
      if (reconnectAttempts.value === 1 || reconnectAttempts.value >= 3) {
        ElNotification({
          title: '连接断开',
          message: '群聊连接已断开，正在尝试重连...',
          type: 'warning',
          duration: 0
        });
      }
      
      reconnectTimer.value = setTimeout(() => {
        if (reconnectAttempts.value >= maxReconnectAttempts) {
          ElNotification({
            title: '连接失败',
            message: '无法连接到服务器，请检查网络连接',
            type: 'error',
            duration: 0
          });
          reconnecting.value = false;
          return;
        }
        
        initWebSocket();
        reconnecting.value = false;
      }, delay);
    };
    
    // 停止重连
    const stopReconnect = () => {
      if (reconnectTimer.value) {
        clearTimeout(reconnectTimer.value);
        reconnectTimer.value = null;
        reconnecting.value = false;
      }
    };
    
    // 添加消息
    const addMessage = (msg) => {
      // 检查是否已存在相同消息
      const exists = messages.value.some(m => m.id === msg.id);
      if (!exists) {
        messages.value.push(msg);
        nextTick(() => {
          if (messagesContainer.value) {
            messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
          }
        });
      }
    };
    
    // 更新最近聊天
    const updateRecentChat = () => {
      store.commit('chat/ADD_RECENT_CHAT', {
        id: targetGroup.value.id,
        username: displayGroupName.value,
        // photo: targetGroup.value.photo,
        avatar_members: targetGroup.value.avatar_members,
        isGroup: true,
        lastMessage: messages.value[messages.value.length - 1]?.text || '',
        lastMessageTime: new Date().toISOString()
      });
      store.dispatch('chat/saveRecentChat');
    };

    // 处理文件上传
    const handleFileUpload = async (event) => {
      const file = event.target.files[0];
      if (!file) return;
      
      try {
        isUploading.value = true;
        uploadProgress.value = 0;
        
        const formData = new FormData();
        formData.append('file', file);
        
        const res = await axios.post(`${API_CONFIG.BASE_URL}/ws/chat/upload/media`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
            'Authorization': `Bearer ${store.state.token}`
          },
          onUploadProgress: (progressEvent) => {
            uploadProgress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          }
        });
        
        if (res.data.success) {
          const mediaType = res.data.type;
          const mediaUrl = res.data.url;
          const original_name = res.data.original_name;
          const size = res.data.size;
          
          sendMediaMessage(mediaType, mediaUrl, original_name, size);
          
          ElMessage.success(`${mediaType === 'image' ? '图片' : mediaType === 'video' ? '视频' : '文件'}上传成功`);
        } else {
          ElMessage.error('上传失败：' + res.data.message);
        }
      } catch (error) {
        console.error('文件上传错误', error);
        ElMessage.error('上传失败，请重试');
      } finally {
        isUploading.value = false;
        uploadProgress.value = 0;
        
        if (fileInput.value) {
          fileInput.value.value = '';
        }
      }
    };
    
    // 发送媒体消息
    const sendMediaMessage = (type, url, original_name, size) => {
      if (!isConnected.value) {
        ElMessage.warning('当前连接已断开，无法发送消息');
        return;
      }
      
      const msg = {
        id: Date.now(),
        text: '',
        media: [{ type, url, original_name, size }],
        fromMe: true,
        time: new Date().toISOString()
      };
      
      addMessage(msg);
      
      try {
        socket.value.send(JSON.stringify({
          id: msg.id,
          text: '',
          media: msg.media,
          time: msg.time,
          from_id: myId.value,
          group_id: targetGroup.value.id,
          from_username: myUser.value.username,
          from_photo: myUser.value.photo
        }));
      } catch (error) {
        console.error('发送媒体消息失败', error);
        ElMessage.error('消息发送失败，请稍后再试');
      }
      
      updateRecentChat();
    };
    
    // 发送文本消息
    const sendMessage = () => {
      const content = inputMessage.value.trim();
      if (!content) {
        ElMessage.warning('消息内容不能为空，请输入后再发送～');
        return;
      }
      
      if (!isConnected.value) {
        ElMessage.warning('当前连接已断开，无法发送消息');
        return;
      }
      
      const msg = {
        id: Date.now(),
        text: inputMessage.value.trim(),
        fromMe: true,
        time: new Date().toISOString()
      };
      
      addMessage(msg);
      inputMessage.value = '';
      
      try {
        socket.value.send(JSON.stringify({
          id: msg.id,
          text: msg.text,
          time: msg.time,
          from_id: myId.value,
          group_id: targetGroup.value.group_id,
          from_username: myUser.value.username,
          from_photo: myUser.value.photo
        }));
      } catch (error) {
        console.error('发送消息失败', error);
        ElMessage.error('消息发送失败，请稍后再试');
      }

      updateRecentChat();
    };
    
    // 返回
    const goBack = () => {
      router.back();
      stopReconnect();
      if (socket.value) {
        socket.value.close();
      }
    };
    
    // 获取发送者头像
    const getSenderAvatar = (msg) => {
      if (msg.fromMe) return myAvatar.value;
    
      // 直接使用消息中的头像信息
      return msg.from_photo ? getFullUrl(msg.from_photo) : defaultAvatar;
    };
    
// 查找发送者名称
const findSenderName = (msg) => {
  if (msg.fromMe) return '我'; // 如果是自己发送的消息
  return msg.from_username || `用户${msg.fromId}`; // 直接使用消息中的用户名
};

    // 获取群信息
    const fetchGroupInfo = async (groupId) => {
      console.log("开始获取群信息:", groupId);
      isLoading.value = true;
      loadError.value = null;
      
      try {
        const res = await axios.get(`${API_CONFIG.BASE_URL}/group/${groupId}`, {
          headers: { Authorization: `Bearer ${store.state.token}` }
        });
        
        if (res.data && res.data.group_id) {
          
          messages.value = [];
          stopReconnect();
          
          targetGroup.value = res.data;
          groupMembers.value = res.data.group_members || [];
          
          // 获取群头像成员
          const avatarMembers = await store.dispatch('chat/fetchGroupAvatar', groupId);
          targetGroup.value.avatarMembers = avatarMembers || [];
          
          if (myId.value) {
            initWebSocket();
          } else {
            console.error("用户未登录，无法初始化WebSocket连接");
            loadError.value = '用户未登录，请重新登录';
          }
        } else {
          throw new Error('群聊信息为空');
        }
      } catch (err) {
        console.error('获取群聊信息失败', err);
        loadError.value = '获取群聊信息失败，请稍后重试';
        isLoading.value = false;
      }
    };
    
    // 点击外部关闭表情选择器
    const handleOutsideClick = (event) => {
      if (showEmojiPicker.value) {
        const emojiPicker = document.querySelector('.emoji-picker');
        const emojiBtn = document.querySelector('.emoji-btn');
        
        if (emojiPicker && !emojiPicker.contains(event.target) && 
            emojiBtn && !emojiBtn.contains(event.target)) {
          showEmojiPicker.value = false;
        }
      }
    };
    console.log("route.params_1: ", route.params)
    // 监听路由变化
    watch(() => route.params.id, (newId) => {
      console.log("newId", newId)
      if (newId) {
        fetchGroupInfo(newId);
      }
    });

    // 组件挂载
    onMounted(() => {
      if (route.params.id) {
        console.log("route.params: ", route.params)
        fetchGroupInfo(route.params.id);
      } else {
        loadError.value = '未指定群聊ID';
        isLoading.value = false;
      }
      
      document.addEventListener('click', handleOutsideClick);
    });
    
    // 组件卸载
    onUnmounted(() => {
      stopReconnect();
      if (socket.value) {
        socket.value.close();
      }
      
      document.removeEventListener('click', handleOutsideClick);
    });

    return {
      targetGroup,
      messages,
      inputMessage,
      myAvatar,
      getFullUrl,
      getFileName,
      formatTime,
      formatMessage,
      sendMessage,
      goBack,
      messagesContainer,
      isConnected,
      showEmojiPicker,
      messageInput,
      fileInput,
      uploadProgress,
      isUploading,
      toggleEmojiPicker,
      handleFileUpload,
      insertEmoji,
      getFileIcon,
      formatFileSize,
      emojis,
      groupMembers,
      getSenderAvatar,
      findSenderName,
      isLoading,
      loadError,
      displayGroupName,
      groupAvatarUrls,
      getAvatarPosition,
      showGroupInfo,
      handleGroupUpdated,
      handleGroupExited
    };
  }
}
</script>

<style scoped>
/* 保持原有的样式不变 */
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #f5f5f5;
}

.chat-header {
  display: flex;
  align-items: center;
  padding: 0 15px;
  height: 50px;
  background-color: #fff;
  border-bottom: 1px solid #e5e5e5;
  position: relative;
}

.back-button {
  position: absolute;
  left: 15px;
  cursor: pointer;
  font-size: 16px;
}

.chat-title {
  flex: 1;
  text-align: center;
  font-weight: bold;
  font-size: 16px;
}

.chat-avatar {
  position: absolute;
  right: 15px;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  overflow: hidden;
}

.group-avatar {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  overflow: hidden;
  background-color: #f0f2f5;
}

.group-avatar-member {
  position: absolute;
  overflow: hidden;
  border-radius: 50%;
  border: 1px solid white;
  box-sizing: border-box;
}

.group-avatar-member img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
  background-color: #f0f2f5;
}

.empty-chat {
  text-align: center;
  color: #999;
  padding-top: 30px;
  font-size: 14px;
}

.message-item {
  display: flex;
  margin-bottom: 15px;
  max-width: 80%;
}

.from-me {
  flex-direction: row-reverse;
  margin-left: auto; /* 靠右对齐 */
}

.from-other {
  flex-direction: row;
  margin-right: auto; /* 靠左对齐 */
}
.message-avatar {
  width: 36px;
  height: 36px;
  margin: 0 8px;
  flex-shrink: 0;
  align-self: flex-end;
}

.avatar-sm {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.message-content {
  max-width: calc(100% - 44px);
  display: flex;
  flex-direction: column;
}

.message-sender {
  font-size: 12px;
  color: #666;
  margin-bottom: 3px;
}

.message-bubble {
  padding: 8px 12px;
  border-radius: 18px;
  position: relative;
  word-break: break-word;
  font-size: 14px;
  line-height: 1.4;
}
.from-other .message-bubble {
  background-color: white;
  color: #333;
  border-top-left-radius: 4px; /* 左侧消息的左侧圆角较小 */
}

.from-me .message-bubble {
  background-color: #1890ff;
  color: white;
  border-top-right-radius: 4px; /* 右侧消息的右侧圆角较小 */
}

.from-other .message-bubble {
  margin-right: 0;
  margin-left: 8px;
  border-top-left-radius: 4px;
  border-bottom-left-radius: 4px;
}

.message-time {
  font-size: 10px;
  color: #999;
  margin-top: 3px;
  text-align: right;
}

.message-media {
  margin-top: 5px;
  border-radius: 8px;
  overflow: hidden;
}

.message-media img {
  max-width: 100%;
  max-height: 200px;
  border-radius: 8px;
  cursor: pointer;
}

.message-media video {
  max-width: 100%;
  max-height: 200px;
  border-radius: 8px;
}

.message-media a {
  display: flex;
  align-items: center;
  background-color: #f0f0f0;
  padding: 8px;
  border-radius: 8px;
  text-decoration: none;
  color: #333;
  font-size: 12px;
}

.message-media a i {
  margin-right: 8px;
  font-size: 16px;
}

.chat-input-area {
  padding: 10px 15px;
  background-color: #fff;
  border-top: 1px solid #e5e5e5;
  position: relative;
}

.connection-status {
  position: absolute;
  top: -20px;
  left: 0;
  right: 0;
  text-align: center;
  background-color: #f5222d;
  color: white;
  font-size: 12px;
  padding: 2px;
  border-radius: 4px 4px 0 0;
}

.media-toolbar {
  margin-bottom: 8px;
}

.media-buttons {
  display: flex;
  gap: 12px;
}

.tooltip-container {
  position: relative;
  display: inline-block;
}

.tooltip {
  visibility: hidden;
  width: auto;
  background-color: #555;
  color: #fff;
  text-align: center;
  border-radius: 4px;
  padding: 4px 8px;
  position: absolute;
  z-index: 1;
  bottom: 125%;
  left: 50%;
  transform: translateX(-50%);
  opacity: 0;
  transition: opacity 0.3s;
  font-size: 12px;
  white-space: nowrap;
}

.tooltip-container:hover .tooltip {
  visibility: visible;
  opacity: 1;
}

.media-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  font-size: 16px;
}

.media-button:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: #1890ff;
}

.media-button input[type="file"] {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.emoji-btn {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #666;
  font-size: 18px;
  cursor: pointer;
  z-index: 1;
  transition: color 0.2s;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.emoji-btn:hover {
  color: #1890ff;
}

.upload-progress {
  position: absolute;
  top: -6px;
  left: 0;
  right: 0;
  height: 3px;
  background-color: #e0e0e0;
  border-radius: 2px;
  overflow: hidden;
}

.upload-progress-bar {
  height: 100%;
  background-color: #1890ff;
  transition: width 0.3s;
}

.input-wrapper input {
  flex: 1;
  height: 40px;
  padding: 0 40px 0 40px;
  border: 1px solid #e5e5e5;
  border-radius: 20px;
  outline: none;
  font-size: 14px;
  background-color: #fafafa;
  transition: all 0.2s;
}

.input-wrapper input:focus {
  background-color: #fff;
  border-color: #1890ff;
}

.input-wrapper input:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

.send-button {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  background-color: #e6e6e6;
  color: #999;
  cursor: not-allowed;
  transition: all 0.2s;
}

.send-button.active {
  background-color: #1890ff;
  color: white;
  cursor: pointer;
}

.send-button i {
  font-size: 14px;
}

.emoji-picker {
  position: absolute;
  bottom: 100%;
  left: 0;
  width: 100%;
  background-color: white;
  border-radius: 12px 12px 0 0;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.12);
  padding: 8px;
  z-index: 100;
  max-height: 200px;
  overflow-y: auto;
  margin-bottom: 10px;
  animation: fadeInUp 0.15s ease-out;
}

.emoji-grid {
  display: grid;
  grid-template-columns: repeat(15, 1fr);
  gap: 0;
}

.emoji-item {
  font-size: 20px;
  padding: 4px;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s;
  border-radius: 6px;
  line-height: 1.2;
  user-select: none;
  -webkit-user-select: none;
}

.emoji-item:hover {
  background-color: #f5f5f5;
  transform: scale(1.15);
}

.file-message {
  display: flex;
  align-items: center;
  width: 100%;
  max-width: 280px;
  padding: 12px;
  background-color: #f9f9f9;
  border-radius: 8px;
  text-decoration: none;
  color: #333;
  transition: all 0.2s;
  border: 1px solid #eaeaea;
}

.file-message:hover {
  background-color: #f0f0f0;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.file-icon {
  margin-right: 12px;
  font-size: 28px;
  color: #1890ff;
}

.file-info {
  flex: 1;
  overflow: hidden;
}

.file-name {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 12px;
  color: #999;
}

.file-download {
  color: #1890ff;
}

.fa-file-image-o { color: #f39c12; }
.fa-file-video-o { color: #e74c3c; }
.fa-file-audio-o { color: #9b59b6; }
.fa-file-pdf-o { color: #e74c3c; }
.fa-file-word-o { color: #2b579a; }
.fa-file-excel-o { color: #217346; }
.fa-file-powerpoint-o { color: #d24726; }
.fa-file-text-o { color: #666; }
.fa-file-archive-o { color: #f39c12; }
.fa-file-o { color: #7f8c8d; }

@media (max-width: 480px) {
  .message-item {
    max-width: 90%;
  }
  
  .emoji-grid {
    grid-template-columns: repeat(8, 1fr);
  }
  
  .emoji-item {
    font-size: 20px;
    padding: 3px 1px;
  }
  
  .chat-header {
    height: 45px;
  }
  
  .chat-title {
    font-size: 14px;
  }
}
</style>