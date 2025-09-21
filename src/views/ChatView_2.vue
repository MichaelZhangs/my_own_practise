<template>
  <div class="chat-view">
    <div class="chat-header">
      <div class="back-button" @click="goBack">
        <i class="fa fa-arrow-left" aria-hidden="true"></i>
      </div>
      <div class="chat-title">{{ targetUser.username || '未知用户' }}</div>
      <div class="chat-avatar">
        <img 
          :src="getFullUrl(targetUser.photo || defaultAvatar)" 
          alt="对方头像" 
          class="avatar" 
          onerror="this.src='@/assets/default-avatar.png'"
        />
      </div>
    </div>
    
    <div class="chat-messages" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-chat">
        开始和 {{ targetUser.username || '对方' }} 聊天吧
      </div>
      
      <div 
        v-for="(msg, index) in messages || []" 
        :key="msg.id || index" 
        :class="['message-item', msg.fromMe ? 'from-me' : 'from-other']"
      >
        <div class="message-avatar">
          <img 
            :src="msg.fromMe ? myAvatar : getFullUrl(targetUser.photo || defaultAvatar)" 
            alt="头像" 
            class="avatar-sm" 
            onerror="this.src='@/assets/default-avatar.png'"
          />
        </div>
        
        <div class="message-content">
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
            class="emoji-item  cursor-pointer hover:bg-gray-100 p-1 text-center"
            @click="insertEmoji(emoji)"
          >
            {{ emoji }}
          </span>
        </div>
      </div>
    </div>
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
import emojis from '@/utils/emojis';

export default {
  setup() {
    const route = useRoute();
    const router = useRouter();
    const store = useStore();
    const messagesContainer = ref(null);
    const targetUser = ref({});
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
    
    const showEmojiPicker = ref(false);
    const messageInput = ref(null);
    const fileInput = ref(null);
    const uploadProgress = ref(0);
    const isUploading = ref(false);

    // 重连相关变量
    const reconnectAttempts = ref(0);
    const maxReconnectAttempts = 5;
    const connectionTimeout = ref(null);

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
  // 确保item是对象且包含url或original_name
  if (!item || typeof item !== 'object') return 'fa fa-file-o';
  
  // 优先使用original_name判断
  const fileName = item.original_name || '';
  const url = item.url || '';
  const contentType = item.content_type || '';
  
  // 获取文件扩展名
  let ext = '';
  if (fileName.includes('.')) {
    ext = fileName.split('.').pop().toLowerCase();
  } else if (url.includes('.')) {
    ext = url.split('.').pop().toLowerCase();
  }
  
  // 根据内容类型判断
  if (contentType.includes('image')) return 'fa fa-file-image-o';
  if (contentType.includes('video')) return 'fa fa-file-video-o';
  if (contentType.includes('audio')) return 'fa fa-file-audio-o';
  if (contentType.includes('pdf')) return 'fa fa-file-pdf-o';
  if (contentType.includes('word')) return 'fa fa-file-word-o';
  if (contentType.includes('excel') || contentType.includes('spreadsheet')) 
    return 'fa fa-file-excel-o';
  if (contentType.includes('powerpoint') || contentType.includes('presentation')) 
    return 'fa fa-file-powerpoint-o';
  if (contentType.includes('zip') || contentType.includes('compressed') || contentType.includes('archive'))
    return 'fa fa-file-archive-o';
  if (contentType.includes('text') || contentType.includes('plain'))
    return 'fa fa-file-text-o';
  if (contentType.includes('html') || contentType.includes('xml'))
    return 'fa fa-file-code-o';
  if (contentType.includes('javascript'))
    return 'fa fa-file-code-o javascript-icon';
  
  // 根据扩展名判断（更详细的映射）
  const iconMap = {
    // 文档文件
    'doc': 'fa fa-file-word-o',
    'docx': 'fa fa-file-word-o',
    'odt': 'fa fa-file-word-o',
    'rtf': 'fa fa-file-text-o',
    
    // 表格文件
    'xls': 'fa fa-file-excel-o',
    'xlsx': 'fa fa-file-excel-o',
    'ods': 'fa fa-file-excel-o',
    'csv': 'fa fa-file-excel-o',
    
    // 幻灯片文件
    'ppt': 'fa fa-file-powerpoint-o',
    'pptx': 'fa fa-file-powerpoint-o',
    'odp': 'fa fa-file-powerpoint-o',
    
    // PDF文件
    'pdf': 'fa fa-file-pdf-o',
    
    // 文本文件
    'txt': 'fa fa-file-text-o',
    'md': 'fa fa-file-text-o',
    'log': 'fa fa-file-text-o',
    
    // 压缩文件
    'zip': 'fa fa-file-archive-o',
    'rar': 'fa fa-file-archive-o',
    '7z': 'fa fa-file-archive-o',
    'tar': 'fa fa-file-archive-o',
    'gz': 'fa fa-file-archive-o',
    
    // 可执行文件和安装包
    'exe': 'fa fa-cog',
    'msi': 'fa fa-cog',
    'dmg': 'fa fa-cog',
    'pkg': 'fa fa-cog',
    'deb': 'fa fa-cog',
    'rpm': 'fa fa-cog',
    'apk': 'fa fa-mobile',
    'app': 'fa fa-cog',
    'bat': 'fa fa-terminal',
    'sh': 'fa fa-terminal',
    'cmd': 'fa fa-terminal',
    
    // 代码文件
    'js': 'fa fa-file-code-o javascript-icon',
    'jsx': 'fa fa-file-code-o react-icon',
    'ts': 'fa fa-file-code-o typescript-icon',
    'tsx': 'fa fa-file-code-o react-icon',
    'html': 'fa fa-file-code-o html-icon',
    'htm': 'fa fa-file-code-o html-icon',
    'css': 'fa fa-file-code-o css-icon',
    'scss': 'fa fa-file-code-o css-icon',
    'sass': 'fa fa-file-code-o css-icon',
    'less': 'fa fa-file-code-o css-icon',
    'py': 'fa fa-file-code-o python-icon',
    'java': 'fa fa-file-code-o java-icon',
    'cpp': 'fa fa-file-code-o cpp-icon',
    'c': 'fa fa-file-code-o c-icon',
    'h': 'fa fa-file-code-o c-header-icon',
    'php': 'fa fa-file-code-o php-icon',
    'rb': 'fa fa-file-code-o ruby-icon',
    'go': 'fa fa-file-code-o go-icon',
    'swift': 'fa fa-file-code-o swift-icon',
    'kt': 'fa fa-file-code-o kotlin-icon',
    'json': 'fa fa-file-code-o',
    'xml': 'fa fa-file-code-o',
    'yml': 'fa fa-file-code-o',
    'yaml': 'fa fa-file-code-o',
    
    // 图像文件
    'jpg': 'fa fa-file-image-o',
    'jpeg': 'fa fa-file-image-o',
    'png': 'fa fa-file-image-o',
    'gif': 'fa fa-file-image-o',
    'bmp': 'fa fa-file-image-o',
    'svg': 'fa fa-file-image-o',
    'webp': 'fa fa-file-image-o',
    'ico': 'fa fa-file-image-o',
    'tiff': 'fa fa-file-image-o',
    'psd': 'fa fa-file-image-o',
    'ai': 'fa fa-file-image-o',
    
    // 视频文件
    'mp4': 'fa fa-file-video-o',
    'avi': 'fa fa-file-video-o',
    'mov': 'fa fa-file-video-o',
    'wmv': 'fa fa-file-video-o',
    'flv': 'fa fa-file-video-o',
    'webm': 'fa fa-file-video-o',
    'mkv': 'fa fa-file-video-o',
    'mpeg': 'fa fa-file-video-o',
    'mpg': 'fa fa-file-video-o',
    
    // 音频文件
    'mp3': 'fa fa-file-audio-o',
    'wav': 'fa fa-file-audio-o',
    'ogg': 'fa fa-file-audio-o',
    'flac': 'fa fa-file-audio-o',
    'aac': 'fa fa-file-audio-o',
    'wma': 'fa fa-file-audio-o',
    'm4a': 'fa fa-file-audio-o',
    
    // 字体文件
    'ttf': 'fa fa-font',
    'otf': 'fa fa-font',
    'woff': 'fa fa-font',
    'woff2': 'fa fa-font',
    'eot': 'fa fa-font',
    
    // 数据库文件
    'sql': 'fa fa-database',
    'db': 'fa fa-database',
    'sqlite': 'fa fa-database',
    'mdb': 'fa fa-database',
    
    // 配置文件
    'ini': 'fa fa-cog',
    'conf': 'fa fa-cog',
    'config': 'fa fa-cog',
    'properties': 'fa fa-cog',
    'env': 'fa fa-cog',
    
    // 其他特殊文件
    'iso': 'fa fa-compact-disc',
    'torrent': 'fa fa-magnet',
    'dll': 'fa fa-puzzle-piece',
    'so': 'fa fa-puzzle-piece',
    'lib': 'fa fa-puzzle-piece',
    
    // 默认文件图标
    'default': 'fa fa-file-o'
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

    const initWebSocket = () => {
      if (myId.value && targetUser.value.id) {
        const wsUrl = `ws://${API_CONFIG.URL_CHAT}/ws/chat/${myId.value}/${targetUser.value.id}`;
        
        if (socket.value) {
          socket.value.onclose = null; // 防止关闭时触发重连
          socket.value.onerror = null;
          socket.value.close();
        }
        
        socket.value = new WebSocket(wsUrl);
       
        socket.value.onopen = () => {
          isConnected.value = true;
          reconnecting.value = false;
          ElNotification({
            title: '连接成功',
            message: `已与 ${targetUser.value.username || '对方'} 建立聊天连接`,
            type: 'success',
            duration: 3000
          });
          loadHistoryMessages();
        };
        
        socket.value.onmessage = async (event) => {
                  // 重置连接超时计时器
            resetConnectionTimeout();

          try {
            const messageData = JSON.parse(event.data)
            
            addMessage({
              id: messageData.id,
              text: messageData.text,
              media: messageData.media || [],
              fromMe: messageData.from === myId.value,
              time: messageData.time
            });
            
            const senderInfo = {
              id: parseInt(messageData.from, 10),
              username: messageData.fromUsername || '未知用户',
              photo: messageData.fromPhoto
            };
            store.commit('chat/ADD_RECENT_CHAT', senderInfo);
            store.dispatch('chat/saveRecentChat');

          } catch (e) {
            console.error('解析消息失败', e);
            ElMessage.error('接收消息失败');
          }
        };
        
        socket.value.onclose = () => {
          isConnected.value = false;
          
          // 只在页面可见时显示连接断开通知
          if (document.visibilityState === 'visible') {
            ElNotification({
              title: '连接断开',
              message: '聊天连接已断开，正在尝试重连...',
              type: 'warning',
              duration: 0
            });
          }
          
          if (!reconnecting.value) {
            startReconnect();
          }
        };

        
        socket.value.onerror = (errorEvent) => {
          console.error('WebSocket错误', errorEvent);
          // ElMessage.error('聊天连接错误，请稍后再试');
        };
    // 设置连接超时
        connectionTimeout.value = setTimeout(() => {
          if (socket.value && socket.value.readyState !== WebSocket.OPEN) {
            console.log('WebSocket连接超时，尝试重连');
            socket.value.close();
            startReconnect();
          }
        }, 10000); // 10秒超时

      }
    };
    
    const loadHistoryMessages = async () => {
      if (myId.value && targetUser.value.id) {
        try {
          const res = await axios.get(`${API_CONFIG.BASE_URL}/ws/chat/history/${myId.value}/${targetUser.value.id}`, {
            headers: { Authorization: `Bearer ${store.state.token}` }
          });
        if (res.data && res.data.length) {
     
           
             const formattedMessages = res.data.map(msg =>({
                  id: msg.id,
                  text: msg.text,
                  media: msg.media || [],
                  from_id: msg.from_id,
                  target_id: myId.value,
                  fromMe: msg.from_id === myId.value,
                  time: msg.created_at
                })); 
            messages.value = formattedMessages;
            }
            nextTick(() => {
              if (messagesContainer.value) {
                messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
              }
            });
          }catch (err) {
          console.error('加载历史消息失败', err);
          ElMessage.warning('历史消息加载失败');
        }
      }
    };
// 同时修改startReconnect函数中的通知逻辑
const startReconnect = () => {
  if (reconnecting.value || !targetUser.value.id) return;
  
  reconnecting.value = true;
  reconnectAttempts.value++;
  
  // 计算重连延迟（指数退避）
  const delay = Math.min(
    3000 * Math.pow(2, reconnectAttempts.value - 1), 
    30000 // 最大延迟30秒
  );
  
  console.log(`尝试重连 (${reconnectAttempts.value}/${maxReconnectAttempts})，延迟: ${delay/1000}秒`);
  
  // 只在页面可见时显示通知
  if (document.visibilityState === 'visible') {
    // 显示连接断开通知（只在首次断开或长时间无法连接时显示）
    if (reconnectAttempts.value === 1 || reconnectAttempts.value >= 3) {
      ElNotification({
        title: '连接断开',
        message: '聊天连接已断开，正在尝试重连...',
        type: 'warning',
        duration: 0
      });
    }
  }
  
  reconnectTimer.value = setTimeout(() => {
    // 如果达到最大重连次数，提示用户
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      // 只在页面可见时显示
      if (document.visibilityState === 'visible') {
        ElNotification({
          title: '连接失败',
          message: '无法连接到服务器，请检查网络连接',
          type: 'error',
          duration: 0
        });
      }
      reconnecting.value = false;
      return;
    }
    
    initWebSocket();
    reconnecting.value = false;
  }, delay);
};
    // const startReconnect = () => {
    //   if (reconnecting.value || !targetUser.value.id) return;
      
    //   reconnecting.value = true;
    //   reconnectTimer.value = setTimeout(() => {
    //     initWebSocket();
    //     reconnecting.value = false;
    //   }, 3000);
    // };
    
    const stopReconnect = () => {
      if (reconnectTimer.value) {
        clearTimeout(reconnectTimer.value);
        reconnectTimer.value = null;
        reconnecting.value = false;
      }
    };
    
    const addMessage = (msg) => {
      messages.value.push(msg);
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
        }
      });
    };
    
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
          const size = res.data.size
          console.log("发送的消息: ", mediaType, mediaUrl,original_name,size)
          sendMediaMessage(mediaType, mediaUrl,original_name,size);
          
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
    
    const sendMediaMessage = (type, url,original_name,size) => {
      if (!isConnected.value) {
        ElMessage.warning('当前连接已断开，无法发送消息');
        return;
      }
      
      const msg = {
        id: Date.now(),
        text: '',
        media: [{ type, url,original_name,size }],
        fromMe: true,
        time: new Date().toISOString()
      };
      console.log("发送的信息msg: ", msg)
      addMessage(msg);
      
      try {
        socket.value.send(JSON.stringify({
          id: msg.id,
          text: '',
          media: msg.media,
          time: msg.time,
          from: myId.value,
          to: targetUser.value.id,
          fromUsername: myUser.value.username,
          fromPhoto: myUser.value.photo
        }));
      } catch (error) {
        console.error('发送媒体消息失败', error);
        ElMessage.error('消息发送失败，请稍后再试');
      }
      
      store.commit('chat/ADD_RECENT_CHAT', targetUser.value);
      store.dispatch('chat/saveRecentChat');
    };
    
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
        media: inputMessage.value.media,
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
          from: myId.value,
          media: msg.media,
          to: targetUser.value.id,
          fromUsername: myUser.value.username,
          fromPhoto: myUser.value.photo
        }));
      } catch (error) {
        console.error('发送消息失败', error);
        ElMessage.error('消息发送失败，请稍后再试');
      }

      store.commit('chat/ADD_RECENT_CHAT', targetUser.value);
      store.dispatch('chat/saveRecentChat');
    };
    
    const goBack = () => {
      router.back();
      stopReconnect();
      if (socket.value) {
        socket.value.close();
      }
    };
    
    watch(() => route.params.id, (newId) => {  // userId ->id
      console.log("单独聊天id : ", newId)
      if (newId) {
        fetchUserInfo(newId);
      }
    });

    const fetchUserInfo = (userId) => {
      // 判断是否是群组ID（以group_开头）
      if (typeof userId === 'string' && userId.startsWith('group_')) {
        console.log('检测到群组ID，跳过用户信息查询');
        // 如果是群组ID，直接设置targetUser并初始化WebSocket
        targetUser.value = {
          id: userId,
          username: '群聊', // 临时名称，后续会被群组信息替换
          isGroup: true
        };
        // 清空聊天记录
        messages.value = [];
        // 停止之前的重连尝试
        stopReconnect();
        initWebSocket();
        return;
      }

      axios.get(`${API_CONFIG.BASE_URL}/user/info`, {
        params: { id: userId },
        headers: { Authorization: `Bearer ${store.state.token}` }
      })
      .then(res => {
        if (res.data && res.data.id) {
                // 清空聊天记录
          messages.value = [];
                // 停止之前的重连尝试
          stopReconnect();
          targetUser.value = res.data;
          initWebSocket();
        } else {
          throw new Error('用户信息为空');
        }
      })
      .catch(err => {
        console.error('获取用户信息失败', err);
        // ElMessage.error('获取用户信息失败');
        router.back();
      });
    };
    
    onMounted(() => {
      if (route.params.id) { // userId ->id
        fetchUserInfo(route.params.id);  // userId ->id
      } else {
        ElMessage.error('未指定聊天对象');
        router.back();
      }
      
      document.addEventListener('click', handleOutsideClick);
    });
    
    onUnmounted(() => {
      stopReconnect();
      if (socket.value) {
        socket.value.close();
      }
      
      document.removeEventListener('click', handleOutsideClick);
    });
    
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

    return {
      targetUser,
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
      emojis
    };
  }
};
</script>

<style scoped>
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

.avatar {
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

/* 我的消息样式 - 头像在右 */
.from-me {
  flex-direction: row-reverse; /* 反转flex方向使头像在右 */
  margin-left: auto;
}

.from-other {
  justify-content: flex-start;
  margin-right: auto;
}

/* 头像样式 */
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

/* 消息内容样式 */
.message-content {
  max-width: calc(100% - 44px);
  display: flex;
  flex-direction: column;
}

.message-bubble {
  padding: 8px 12px;
  border-radius: 18px;
  position: relative;
  word-break: break-word;
  font-size: 14px;
  line-height: 1.4;
  background-color: #1890ff;
  color: white;
}

.from-other .message-bubble {
  background-color: white;
  color: #333;
}

/* 调整气泡位置 */
.from-me .message-bubble {
  margin-left: 0;
  margin-right: 8px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
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

/* 输入区域样式 */
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

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
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

.emoji-picker::-webkit-scrollbar {
  width: 6px;
}

.emoji-picker::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

/* 响应式调整 */
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

/* 文件消息样式 */
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

/* 文件图标颜色 */
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
/* 可执行文件样式 */
.fa-cog {
  color: #ff4757; /* 红色 */
}

/* 代码文件样式 */
.javascript-icon { color: #f7df1e; }
.python-icon { color: #3776ab; }
.html-icon { color: #e34f26; }
.css-icon { color: #1572b6; }

/* 压缩文件样式 */
.fa-file-archive-o {
  color: #e67e22; /* 橙色 */
}

/* 配置文件样式 */
.fa-cog:not([class*="fa-file"]) {
  color: #95a5a6; /* 灰色 */
}
</style>
