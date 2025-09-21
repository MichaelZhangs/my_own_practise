<template>
  <div class="user-detail-moment-page">
    <!-- 左侧用户信息栏 -->
      <div class="user-profile" @click="goToUserInfo(currentUser.id)">
        <img
          :src="getFullUrl(currentUser.photo) || defaultAvatar"
          class="sidebar-avatar"
        />
        <!-- <span class="sidebar-username">{{ currentUser.username }}</span> -->
    </div>

    <!-- 头部容器 -->
    <div class="detail-header fixed top-0 left-0 right-0 bg-white shadow-md h-16 z-10">
      <div class="header-content">
        <div class="title-container">
          <h1>动态详情</h1>
        </div>
      </div>
    </div>

    <!-- 动态内容容器 -->
    <div class="moment-detail-container">
      <div v-if="moment.id" class="moment-item">
        <!-- 用户信息 -->
        <div class="user-info">
          <img
            :src="getFullUrl(moment.user.photo) || defaultAvatar"
            class="user-avatar"
            @click="goToUserInfo(moment.user_id)"
          />
          <div class="user-details">
            <span class="username" @click="goToUserInfo(moment.user.id)">{{ moment.user.username }}</span>
            <span class="post-time">{{ formatTime(moment.created_at) }}</span>
          </div>
        </div>

        <!-- 动态内容 -->
        <div class="moment-content" v-html="sanitizeHtml(moment.content)"></div>

        <!-- 媒体内容 -->
        <div v-if="moment.media?.length" class="media-grid">
          <div
            v-for="(media, index) in moment.media"
            :key="index"
            class="media-item"
            :class="{ 'video-container': media.type === 'video' }"
          >
            <img
              v-if="media.type === 'image'"
              :src="getFullUrl(media.url)"
              @click="openImagePreview(getFullUrl(media.url))"
            />
            <video
              v-else-if="media.type === 'video'"
              :src="getFullUrl(media.url)"
              controls
              :poster="getFullUrl(media.thumbnail)"
            >
              <source :src="getFullUrl(media.url)" :type="getVideoType(media.url)">
              您的浏览器不支持视频播放
            </video>

                            <audio
                v-else-if="media.type === 'audio'"
                :src="getFullUrl(media.url)"
                controls
                :poster="getFullUrl(media.thumbnail)"
              >
                <source :src="getFullUrl(media.url)" :type="getVideoType(media.url)">
                您的浏览器不支持视频播放
              </audio>
          </div>
        </div>

        <!-- 互动区域 -->
        <div class="moment-interaction flex justify-end space-x-4">
          <div class="like-container flex items-center space-x-1 cursor-pointer" @click.stop="likeMoment(moment.id)">
            <i
              class="fa-solid fa-thumbs-up"
              :class="{ 'liked': moment.isLiked }"
            ></i>
            <span>{{ moment.stats.likes }}</span>
          </div>
          <div class="comment-container flex items-center space-x-1 cursor-pointer" @click="toggleCommentInput(moment)">
            <i class="fa-solid fa-comment"></i>
            <span>{{ moment.stats.comments }}</span>
          </div>
          <i
            v-if="moment.user_id === currentUser.id"
            class="fa-solid fa-trash-can delete-btn cursor-pointer hover:text-red-500 transition-colors ml-4"
            @click="deleteMoment(moment.id)"
          ></i>
        </div>

        <!-- 底部信息 - 调整删除按钮位置和间距 -->
        <div class="moment-footer flex items-center text-sm text-gray-500">
          <div class="flex items-center space-x-4">
            <span class="time-ago">{{ getTimeAgo(moment.created_at) }}</span>
          </div>
        </div>

        <!-- 评论输入框 -->
        <div v-if="moment.showCommentInput" class="comment-input-area flex items-center mt-2">
          <div class="relative flex-1">
            <div class="emoji-btn absolute left-3 top-1/2 transform -translate-y-1/2" @click="toggleEmojiPicker(moment, 'comment')">
              <i class="fa-regular fa-face-smile"></i>
            </div>
            <input
              v-model="moment.commentInput"
              type="text"
              placeholder="发表评论..."
              class="w-full border border-gray-300 rounded-full p-2 pl-9 pr-10 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
              @keyup.enter="postComment(moment)"
            />
            <div
              v-if="moment.showEmojiPicker"
              class="emoji-picker absolute bottom-full left-0 right-0 mb-2 bg-white rounded-lg shadow-lg p-1 z-20 max-h-60 overflow-y-auto"
            >
              <div class="emoji-grid">
                <span
                  v-for="(emoji, index) in emojis"
                  :key="index"
                  class="emoji-item cursor-pointer hover:bg-gray-100 p-1 text-center"
                  @click="insertEmoji(moment, 'comment', emoji)"
                >
                  {{ emoji }}
                </span>
              </div>
            </div>
          </div>
          <button
            @click="postComment(moment)"
            class="ml-2 px-4 py-2 rounded-full transition-colors duration-200 whitespace-nowrap"
            :class="moment.commentInput.trim()? 
              'bg-primary text-white hover:bg-primary/90' : 
              'bg-gray-200 text-gray-400 cursor-not-allowed'"
            :disabled="!moment.commentInput.trim()"
          >
            <i class="fa-solid fa-paper-plane mr-1"></i> 发送
          </button>
        </div>

        <!-- 评论列表 -->
        <ul v-if="moment.comments?.length" class="comments-list">
          <li
            v-for="(comment, index) in visibleComments(moment)"
            :key="index"
            class="comment-item py-3"
          >
            <div class="comment-header flex items-center space-x-2">
              <img
                :src="getFullUrl(comment.comment_user_photo) || defaultAvatar"
                class="comment-avatar"
                @click="goToUserInfo(comment.comment_user_id)"
              />
              <div class="comment-user-details flex-1">
                <span class="comment-username" @click="goToUserInfo(comment.comment_user_id)">{{ comment.comment_user_name }}</span>
                <span class="comment-post-time">{{ formatTime(comment.created_at) }}</span>
              </div>
            </div>

            <div class="comment-content mt-1 ml-8 text-gray-600 text-sm">
              {{ comment.comment }}
            </div>

            <!-- 回复操作 - 调整删除按钮位置 -->
            <div class="comment-actions flex justify-between items-center mt-1 text-xs">
              <div class="flex space-x-4">
                <div class="comment-like flex items-center space-x-1" @click.stop="likeComment(moment.id, comment.id)">
                  <i class="fa-solid fa-thumbs-up" :class="{ 'liked': comment.isLiked }"></i>
                  <span>{{ comment.likes }}</span>
                </div>
                <div class="comment-reply flex items-center space-x-1" @click="toggleReplyInput(comment)">
                  <i class="fa-solid fa-comment"></i>
                </div>
              </div>
              <i
                v-if="comment.comment_user_id === currentUser.id"
                class="fa-solid fa-trash-can comment-delete-btn cursor-pointer hover:text-red-500 transition-colors"
                @click="deleteComment(moment.id, comment.id, index)"
              ></i>
            </div>

            <!-- 回复列表 -->
            <div v-if="comment.reply?.length" class="replies-list ml-8 mt-2">
              <div 
                v-for="(reply, replyIndex) in comment.reply"
                :key="reply.id || replyIndex"
                class="reply-item py-3"
              >
                <div class="flex items-center space-x-2">
                  <img
                    :src="getFullUrl(reply.reply_user_photo) || defaultAvatar"
                    class="comment-avatar"
                    @click="goToUserInfo(reply.reply_user_id)"
                  />
                  <span class="text-sm font-medium" @click="goToUserInfo(reply.reply_user_id)">{{ reply.reply_user_name }}</span>
                </div>
                <div class="reply-content ml-7 text-gray-600 text-sm">
                  {{ reply.reply_comment }}
                </div>
                <div class="flex justify-between items-center ml-7 mt-1">
                  <div class="reply-time text-xs text-gray-500">
                    {{ formatTime(reply.created_dt) }}
                  </div>
                  <div class="reply-actions flex space-x-4">
                    <div class="reply-like flex items-center space-x-1" @click.stop="likeReply(moment.id, comment.id, reply.id, replyIndex)">
                      <i class="fa-solid fa-thumbs-up" :class="{ 'liked': reply.isLiked }"></i>
                      <span>{{ reply.likes || 0 }}</span>
                    </div>
                    <div class="reply-reply flex items-center space-x-1" @click="replyToReply(moment, comment, reply)">
                      <i class="fa-solid fa-comment"></i>
                    </div>
                    <i
                      v-if="reply.reply_user_id === currentUser.id"
                      class="fa-solid fa-trash-can reply-delete-btn cursor-pointer hover:text-red-500 transition-colors"
                      @click="deleteReply(moment.id, comment.id, reply.id, replyIndex)"
                    ></i>
                  </div>
                </div>
              </div>
            </div>

            <!-- 回复输入框 - 移到回复按钮下方 -->
            <div v-if="comment.showReplyInput" class="reply-input-area ml-8 mt-2" :data-comment-id="comment.id">
              <div class="relative flex-1">
                <div class="emoji-btn absolute left-3 top-1/2 transform -translate-y-1/2" @click="toggleEmojiPicker(comment, 'reply')">
                  <i class="fa-regular fa-face-smile"></i>
                </div>
                <input
                  v-model="comment.replyInput"
                  type="text"
                  placeholder="回复评论..."
                  class="w-full border border-gray-300 rounded-full p-2 pl-9 pr-10 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
                  @keyup.enter="postReply(moment, comment)"
                />
                <div
                  v-if="comment.showEmojiPicker"
                  class="emoji-picker absolute bottom-full left-0 right-0 mb-2 bg-white rounded-lg shadow-lg p-1 z-20 max-h-60 overflow-y-auto"
                >
                  <div class="emoji-grid">
                    <span
                      v-for="(emoji, index) in emojis"
                      :key="index"
                      class="emoji-item cursor-pointer hover:bg-gray-100 p-1 text-center"
                      @click="insertEmoji(comment, 'reply', emoji)"
                    >
                      {{ emoji }}
                    </span>
                  </div>
                </div>
              </div>
              <button
                @click="postReply(moment, comment)"
                class="ml-2 px-4 py-2 rounded-full transition-colors duration-200 whitespace-nowrap text-sm"
                :class="comment.replyInput.trim()? 
                  'bg-primary text-white hover:bg-primary/90' : 
                  'bg-gray-200 text-gray-400 cursor-not-allowed'"
                :disabled="!comment.replyInput.trim()"
              >
                <i class="fa-solid fa-paper-plane mr-1"></i> 发送
              </button>
            </div>
          </li>

          <!-- 展开更多 -->
          <li 
            v-if="moment.comments.length > 3 && !moment.showAllComments"
            class="show-more-comments text-blue-500 text-sm cursor-pointer pt-2"
            @click="moment.showAllComments = true"
          >
            展开全部{{ moment.comments.length }}条评论
          </li>
        </ul>
      </div>
      <div v-else class="loading-message text-center text-gray-500 mt-10">
        正在加载动态详情...
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useStore } from 'vuex'
import axios from 'axios'
import DOMPurify from 'dompurify'
import defaultAvatar from '@/assets/default-avatar.png'
import { API_CONFIG } from '@/config/config'
import { ElMessage } from 'element-plus'
import emojis from '@/utils/emojis'  // 导入表情数据

export default {
  setup() {
    const router = useRouter()
    const store = useStore()
    const moment = ref({})
    const currentUser = computed(() => store.state.user || {})

    

    // 跳转到用户个人信息页面
    const goToUserInfo = (userId) => {
      router.push(`/user/userinfo/${userId}`)
    }
    
    // 跳转到用户页面（原有的方法保留，可能用于其他地方）
    const goToUser = () => router.push('/user/dashboard')

    const openImagePreview = (url) => {
      window.open(url, '_blank')
    }

    
      const mediaTypeMap = {
  // 音频格式
  '.mp3': 'audio/mpeg',
  '.wav': 'audio/wav',
  '.flac': 'audio/flac',
  '.aac': 'audio/aac',
  '.m4a': 'audio/x-m4a',
  '.oga': 'audio/ogg',
  '.ogg': 'audio/ogg',
  '.wma': 'audio/x-wma',
  '.opus': 'audio/opus',
  
  // 视频格式
  '.mp4': 'video/mp4',
  '.webm': 'video/webm',
  '.ogv': 'video/ogg',
  '.mov': 'video/quicktime',
  '.avi': 'video/x-msvideo',
  '.wmv': 'video/x-ms-wmv',
  
  // 图片格式
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.gif': 'image/gif',
  '.webp': 'image/webp'
};

const getVideoType = (url) => {
  if (!url) return 'application/octet-stream';
  
  const lowerUrl = url.toLowerCase();
  const ext = lowerUrl.split('.').pop(); // 获取文件后缀
  
  // 通过映射表获取类型，无匹配时返回通用类型
  return mediaTypeMap[ext] || 'application/octet-stream';
};

  //   const getVideoType = (url) => {
  // if (!url) return 'video/mp4';
  
  // const lowerUrl = url.toLowerCase();
  
  // // 图片类型判断
  // if (lowerUrl.endsWith('.jpg') || lowerUrl.endsWith('.jpeg')) return 'image/jpeg';
  // if (lowerUrl.endsWith('.png')) return 'image/png';
  // if (lowerUrl.endsWith('.gif')) return 'image/gif';
  // if (lowerUrl.endsWith('.webp')) return 'image/webp';
  
  // // 视频类型判断
  // if (lowerUrl.endsWith('.mp4')) return 'video/mp4';
  // if (lowerUrl.endsWith('.webm')) return 'video/webm';
  // if (lowerUrl.endsWith('.ogg')) return 'video/ogg';
  
  // // 音频类型判断（新增）
  // if (lowerUrl.endsWith('.mp3')) return 'audio/mpeg';
  // if (lowerUrl.endsWith('.wav')) return 'audio/wav';
  // if (lowerUrl.endsWith('.flac')) return 'audio/flac';
  // if (lowerUrl.endsWith('.aac')) return 'audio/aac';
  // if (lowerUrl.endsWith('.m4a')) return 'audio/x-m4a';
  // if (lowerUrl.endsWith('.oga')) return 'audio/ogg'; // 音频ogg格式
  
  //   return 'video/mp4'; // 默认返回视频类型
  //   }

    const getFullUrl = (path) => {
      if (!path || path === defaultAvatar) return path
      return path.startsWith('http')? path : `${API_CONFIG.BASE_URL}${path}`
    }

    const formatTime = (timestamp) => {
      const date = new Date(timestamp)
      return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-` +
             `${date.getDate().toString().padStart(2, '0')} ` +
             `${date.getHours().toString().padStart(2, '0')}:` +
             `${date.getMinutes().toString().padStart(2, '0')}`
    }

    const getTimeAgo = (timestamp) => {
      const now = Date.now()
      const diff = now - new Date(timestamp).getTime()
      const minutes = Math.floor(diff / 60000)
      const hours = Math.floor(minutes / 60)
      const days = Math.floor(hours / 24)

      if (minutes < 1) return '刚刚'
      if (minutes < 60) return `${minutes}分钟前`
      if (hours < 24) return `${hours}小时前`
      return `${days}天前`
    }

    const sanitizeHtml = (html) => DOMPurify.sanitize(html)

    // 获取对应moment 的信息
    const fetchMomentDetail = async (momentId) => {
  try {
    const response = await axios.get(`${API_CONFIG.BASE_URL}/article/moment`, {
      params: { moment_id: momentId },
      headers: { Authorization: `Bearer ${store.state.token}` }
    });
    const msg = response.data
    
    // 处理解密后的动态数据
    moment.value = {
      ...msg,
      showCommentInput: false,
      commentInput: '',
      comments: (msg.comments || []).map(comment => ({
        ...comment,
        showReplyInput: false,
        id: comment.comment_id, 
        replyInput: '',
        reply: (comment.reply || []).map(reply => ({
          ...reply,
          id: reply._id ||  reply.reply_id || reply.id, // 确保回复有id
          likes: reply.stats?.likes || 0,
          isLiked: reply.like_users?.includes(currentUser.value.id) || false,
          showEmojiPicker: false
        })),
        isLiked: comment.like_users?.includes(currentUser.value.id) || false,
        likes: comment.stats?.likes || 0,
        showEmojiPicker: false
      })),
      showAllComments: false,
      isLiked: msg.like_users?.includes(currentUser.value.id) || false,
      showEmojiPicker: false
    };
    
    // console.log('动态详情加载成功:', moment.value);
  } catch (error) {
    console.error('获取动态详情失败:', error);
    ElMessage.error('加载动态详情失败');
  }
};
    // const fetchMomentDetail = async (momentId) => {
    //   try {
    //     const response = await axios.get(`${API_CONFIG.BASE_URL}/article/moment`, {
    //       params: { moment_id: momentId },
    //       headers: { Authorization: `Bearer ${store.state.token}` }
    //     })

    //     const momentData = response.data
    //     moment.value = {
    //       ...momentData,
    //       showCommentInput: false,
    //       commentInput: '',
    //       comments: (momentData.comments || []).map(comment => ({
    //         ...comment,
    //         showReplyInput: false,
    //         id: comment.comment_id, 
    //         replyInput: '',
    //         reply: (comment.reply || []).map(reply => ({
    //                   ...reply,
    //                   id: reply._id ||  reply.reply_id || reply.id, // 确保回复有id
    //                   likes: reply.stats?.likes || 0,
    //                   isLiked: reply.like_users?.includes(currentUser.value.id) || false,
    //                   showEmojiPicker: false
    //                 })),
    //         isLiked: comment.like_users?.includes(currentUser.value.id) || false, // 确保初始化点赞状态
    //         likes: comment.stats?.likes || 0 ,// 确保初始化点赞数
    //         showEmojiPicker: false  // 为评论添加表情选择器状态
    //       })),
    //       showAllComments: false,
    //       isLiked: momentData.like_users?.includes(currentUser.value.id) || false,
    //       showEmojiPicker: false  // 为评论输入框添加表情选择器状态
    //     }
    //   } catch (error) {
    //     console.error('获取动态详情失败:', error)
    //     ElMessage.error('加载动态详情失败')
    //   }
    // }

    const toggleCommentInput = (moment) => {
      moment.showCommentInput = !moment.showCommentInput
      moment.commentInput = ''
      moment.showEmojiPicker = false  // 关闭表情选择器
    }

    const postComment = async (moment) => {
      if (!moment.commentInput.trim()) return

      try {
        const response = await axios.post(
          `${API_CONFIG.BASE_URL}/article/post_comment`,
          {
            moment_id: moment.id,
            comment: moment.commentInput,
            comment_user_name: currentUser.value.username,
            comment_user_id: currentUser.value.id
          },
          { headers: { Authorization: `Bearer ${store.state.token}` } }
        )
        if (response.data.msg) {
          moment.comments.unshift({
            id: response.data.id,
            comment: moment.commentInput,
            created_at: new Date().toISOString(),
            comment_user_name: currentUser.value.username,
            comment_user_photo: currentUser.value.photo,
            likes: 0,
            isLiked: false,
            replies: [],
            showReplyInput: false,
            replyInput: '',
            showEmojiPicker: false  // 为新评论添加表情选择器状态
          })
          moment.stats.comments += 1
          moment.commentInput = ''
          moment.showCommentInput = false
          moment.showEmojiPicker = false  // 关闭表情选择器
          ElMessage.success('评论发布成功')
          router.push(`/moment/${moment.id}`)
        }
      } catch (error) {
        console.error('评论失败:', error)
        ElMessage.error('评论发布失败')
      }
    }

    const toggleReplyInput = (comment) => {
      // 使用 setTimeout 延迟执行，避免双击事件立即触发两次
      setTimeout(() => {
        // 先关闭其他所有回复输入框
        if (moment.value.comments) {
          moment.value.comments.forEach(c => {
            if (c !== comment) { // 不关闭当前点击的评论
              c.showReplyInput = false
              c.showEmojiPicker = false
            }
          })
        }
        
        // 切换当前回复输入框状态
        comment.showReplyInput = !comment.showReplyInput
        comment.replyInput = ''
        comment.showEmojiPicker = false
        
        // 为回复输入框添加动画效果
        if (comment.showReplyInput) {
          setTimeout(() => {
            const replyInputArea = document.querySelector(`.reply-input-area[data-comment-id="${comment.id}"]`);
            if (replyInputArea) {
              replyInputArea.classList.add('active');
            }
          }, 10);
        } else {
          const replyInputArea = document.querySelector(`.reply-input-area[data-comment-id="${comment.id}"]`);
          if (replyInputArea) {
            replyInputArea.classList.remove('active');
          }
        }
      }, 100); // 100ms 延迟足够防止双击问题
    }

    const postReply = async (moment, comment) => {
      if (!comment.replyInput.trim()) return

      try {
        const response = await axios.post(
          `${API_CONFIG.BASE_URL}/article/reply_comment`,
          {
            reply_user_name: currentUser.value.username,
            comment_id: comment.id,
            reply_comment: comment.replyInput,
            reply_user_id: currentUser.value.id
          },
          { headers: { Authorization: `Bearer ${store.state.token}` } }
        )
        if (response.data.msg) {
          const newReply = {
            id: response.data.id,
            reply_comment: comment.replyInput,
            created_dt: new Date().toISOString(),
            reply_user_name: currentUser.value.username,
            reply_user_photo: currentUser.value.photo,
            reply_user_id: currentUser.value.id,
            likes: 0,           // 初始化点赞数
            isLiked: false,     // 初始化点赞状态
            showEmojiPicker: false // 添加表情选择器状态
          }
          
          // 确保reply数组存在且为数组类型
          if (!Array.isArray(comment.reply)) {
            comment.reply = [];
          }
          
          // 添加到回复列表开头
          comment.reply.unshift(newReply);
          
          // 清空输入框
          comment.replyInput = '';
          comment.showReplyInput = false;
          comment.showEmojiPicker = false;  // 关闭表情选择器
          
          // 更新评论的回复计数
          comment.reply_count = (comment.reply_count || 0) + 1;
          
          // 更新动态的总评论数
          moment.stats.comments += 1;
          
          ElMessage.success('回复成功');
        }
      } catch (error) {
        console.error('回复失败:', error);
        ElMessage.error('回复失败');
      }
    };

    const likeMoment = async (momentId) => {
      const targetMoment = moment.value
      if (!targetMoment) return

      const originalIsLiked = targetMoment.isLiked
      const originalLikes = targetMoment.stats.likes

      try {
        targetMoment.isLiked = !targetMoment.isLiked
        targetMoment.stats.likes += targetMoment.isLiked? 1 : -1

        const response = await axios.post(`${API_CONFIG.BASE_URL}/article/like_moment`, {
          moment_id: momentId,
          user_id: currentUser.value.id,
          is_like: targetMoment.isLiked
        }, {
          headers: { Authorization: `Bearer ${store.state.token}` },
          timeout: 5000
        })

        if (response.data.msg) {
          if (!targetMoment.stats) {
            targetMoment.stats = { likes: 0 };
          }
          targetMoment.isLiked = response.data.is_liked
          targetMoment.stats.likes = response.data.likes_count
          ElMessage.success(targetMoment.isLiked? '点赞成功' : '已取消点赞')
          router.push(`/moment/${momentId}`)
          if (response.data.is_liked) {
            targetMoment.like_users = [
              ...(targetMoment.like_users || []),
              currentUser.value.id
            ]
          } else {
            targetMoment.like_users = (targetMoment.like_users || [])
              .filter(id => id !== currentUser.value.id)
          }
        }
      } catch (error) {
        targetMoment.isLiked = originalIsLiked
        targetMoment.stats.likes = originalLikes

        console.error('点赞操作失败:', error)
        ElMessage.error(`操作失败: ${error.response?.data?.msg || '网络错误'}`)
      }
    }

    const likeComment = async (momentId, commentId) => {
      // 从评论列表中查找评论对象
      const commentIndex = moment.value.comments.findIndex(c => c.id === commentId)
      if (commentIndex === -1) return
      
      const comment = moment.value.comments[commentIndex]
      if (!comment) return
      
      // 保存原始状态用于回滚
      const originalIsLiked = comment.isLiked
      const originalLikes = comment.likes || 0
      
      try {
        // 立即更新UI状态
        comment.isLiked = !originalIsLiked
        comment.likes = originalIsLiked ? originalLikes - 1 : originalLikes + 1;
        
        // 调用API
        const response = await axios.post(
          `${API_CONFIG.BASE_URL}/article/like_comment`,
          { 
            comment_id: commentId,
            user_id: currentUser.value.id,
            is_like: comment.isLiked
          },
          { headers: { Authorization: `Bearer ${store.state.token}` } }
        )

        // 更新状态
        if (response.data.status_code) {
          comment.isLiked = response.data.is_liked
          comment.likes = response.data.likes_count
          
          ElMessage.success(comment.isLiked ? '点赞成功' : '已取消点赞')
          router.push(`/moment/${momentId}`)
        } else {
          // 如果API返回错误，回滚状态
          comment.isLiked = response.data.isLiked
          comment.likes = response.data.likes_count
          ElMessage.error(response.data.msg || '点赞失败')
        }
      } catch (error) {
        // 发生异常，回滚状态
        comment.isLiked = originalIsLiked
        comment.likes = originalLikes
        console.error('点赞失败:', error)
        ElMessage.error(`点赞失败: ${error.response?.data?.msg || '网络错误'}`)
      }
    }

    // 新增：回复点赞功能
    const likeReply = async (momentId, commentId, replyId, replyIndex) => {
      // 查找评论
      const comment = moment.value.comments.find(c => c.id === commentId)
      if (!comment || !comment.reply || !comment.reply[replyIndex]) return
      
      const reply = comment.reply[replyIndex]
      const originalIsLiked = reply.isLiked
      const originalLikes = reply.likes || 0
      
      try {
        // 立即更新UI状态
        reply.isLiked = !originalIsLiked
        reply.likes = originalIsLiked ? originalLikes - 1 : originalLikes + 1
        
        // 调用API
        const response = await axios.post(
          `${API_CONFIG.BASE_URL}/article/like_reply`,
          {
            reply_id: replyId,
            user_id: currentUser.value.id,
            is_like: reply.isLiked
          },
          { headers: { Authorization: `Bearer ${store.state.token}` } }
        )
        
        // 更新状态
        if (response.data.status_code) {
          reply.isLiked = response.data.is_liked
          reply.likes = response.data.likes_count
          ElMessage.success(reply.isLiked ? '点赞成功' : '已取消点赞')
        } else {
          // 如果API返回错误，回滚状态
          reply.isLiked = originalIsLiked
          reply.likes = originalLikes
          ElMessage.error(response.data.msg || '点赞失败')
        }
      } catch (error) {
        // 发生异常，回滚状态
        reply.isLiked = originalIsLiked
        reply.likes = originalLikes
        console.error('点赞回复失败:', error)
        ElMessage.error(`点赞失败: ${error.response?.data?.msg || '网络错误'}`)
      }
    }

    const replyToReply = (moment, comment, reply) => {
      // 使用可选链操作符安全遍历嵌套结构
      moment?.value?.comments?.forEach(c => {
        c.showReplyInput = false
        c.showEmojiPicker = false
        c.reply?.forEach(r => {
          r.showReplyInput = false
        })
      })
      
      // 打开回复输入框
      if (comment) {
        comment.showReplyInput = true
        comment.replyInput = `@${reply?.reply_user_name || ''}   `
      }
    }

    const deleteMoment = async (momentId) => {
      if (!confirm('确定要删除这条动态吗？')) return

      try {
        await axios.post(
          `${API_CONFIG.BASE_URL}/article/delete/moment`,
          { moment_id: momentId },
          { headers: { Authorization: `Bearer ${store.state.token}` } }
        )
        router.back()
        ElMessage.success('删除成功')
      } catch (error) {
        console.error('删除失败:', error)
        ElMessage.error('删除失败')
      }
    }

    // 删除评论方法
    const deleteComment = async (momentId, commentId, commentIndex) => {
      if (!confirm('确定要删除这条评论吗？')) return

      try {
        await axios.post(
          `${API_CONFIG.BASE_URL}/article/delete/comment`,
          { comment_id: commentId },
          { headers: { Authorization: `Bearer ${store.state.token}` } }
        )

        // 从列表中移除评论
        moment.value.comments.splice(commentIndex, 1)
        // 更新评论数量
        moment.value.stats.comments -= 1
        ElMessage.success('评论已删除')
      } catch (error) {
        console.error('删除评论失败:', error)
        ElMessage.error('删除评论失败')
      }
    }

    // 删除回复方法
    const deleteReply = async (momentId, commentId, replyId, replyIndex) => {
      if (!confirm('确定要删除这条回复吗？')) return
      try {
        await axios.post(
          `${API_CONFIG.BASE_URL}/article/delete/reply`,
          { reply_id: replyId },
          { headers: { Authorization: `Bearer ${store.state.token}` } }
        )

        // 从列表中移除回复
        const comment = moment.value.comments.find(c => c.id === commentId)
        if (comment) {
          comment.reply.splice(replyIndex, 1)
        }
        ElMessage.success('回复已删除')
      } catch (error) {
        console.error('删除回复失败:', error)
        ElMessage.error('删除回复失败')
      }
    }

    const visibleComments = (moment) => {
      return moment.showAllComments? 
        moment.comments : 
        moment.comments.slice(0, 3)
    }

    // 表情选择器相关方法
    const toggleEmojiPicker = (target, type) => {
      // 先关闭所有其他表情选择器
      if (type === 'comment') {
        // 关闭所有评论的表情选择器
        moment.value.comments.forEach(comment => {
          comment.showEmojiPicker = false
        })
      } else {
        // 关闭主评论输入框的表情选择器
        moment.value.showEmojiPicker = false
      }
      
      // 切换当前表情选择器状态
      target.showEmojiPicker = !target.showEmojiPicker
    }

    const insertEmoji = (target, type, emoji) => {
      const inputField = type === 'comment'? target.commentInput : target.replyInput
      const newText = inputField + emoji
      
      if (type === 'comment') {
        target.commentInput = newText
      } else {
        target.replyInput = newText
      }
    }

    onMounted(() => {
      const route = router.currentRoute.value
      const momentId = route.params.momentId
      if (momentId) {
        fetchMomentDetail(momentId)
      }
    })

    onUnmounted(() => {
      // 清理操作
    })

    return {
      moment,
      currentUser,
      getFullUrl,
      formatTime,
      getTimeAgo,
      sanitizeHtml,
      goToUser,
      goToUserInfo, // 导出新的路由方法
      toggleCommentInput,
      postComment,
      toggleReplyInput,
      postReply,
      likeMoment,
      likeComment,
      likeReply, // 新增：导出回复点赞方法
      replyToReply, // 新增：导出回复的回复方法
      deleteMoment,
      visibleComments,
      defaultAvatar,
      openImagePreview,
      getVideoType,
      deleteComment,
      deleteReply,
      emojis,
      toggleEmojiPicker,
      insertEmoji
    }
  }
}
</script>

<style scoped>
/* 其他样式保持不变 */

.emoji-grid {
  display: grid;
  grid-template-columns: repeat(15, 1fr);
  gap: 0;
}

.emoji-item {
  font-size: 20px;
  padding: 4px;
  transition: transform 0.1s;
}

.emoji-item:hover {
  transform: scale(1.3);
  background-color: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
}

.emoji-picker {
  animation: fadeIn 0.2s ease-out;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  max-height: 240px;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

/* 自定义滚动条样式 */
.emoji-picker::-webkit-scrollbar {
  width: 4px;
}

.emoji-picker::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 10px;
}

.emoji-picker::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 10px;
}

.emoji-picker::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

:root {
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 12px;
  --spacing-lg: 16px;
  --spacing-xl: 24px;
  --primary-color: #07c160;
  --text-color: #333;
  --light-text-color: #999;
  --border-color: #eaeaea;
  --bg-color: #f8f8f8;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* 全局动画定义 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-in {
  animation: fadeIn 0.3s ease-out forwards;
}

/* 移动端优化 */
@media (max-width: 640px) {
 .moment-detail-container {
    padding: 0 15px;
    padding-top: 60px;
  }
 .moment-item {
    padding: 15px;
  }
 .media-grid {
    grid-template-columns: repeat(2, 1fr);
  }
 .user-sidebar {
    display: none;
  }
 .detail-header {
    left: 0;
  }
}

/* 侧边栏样式 */
/* .user-sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 240px;
  background: #fff;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
  z-index: 99;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
} */

.user-profile {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  transition: transform 0.2s;
  width: 100%;
}

.user-profile:hover {
  transform: translateX(5px);
}

.sidebar-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  margin-bottom: 15px;
  border: 2px solid var(--primary-color);
  padding: 3px;
  object-fit: cover;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

.sidebar-username {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-color);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
}

/* 视频相关样式 */
.video-container {
  position: relative;
  padding-top: 56.25%; /* 16:9 宽高比 */
  border-radius: 8px;
  overflow: hidden;
}

video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  background: #000;
}

/* 媒体项高度调整 */
.media-item {
  height: 120px;
  overflow: hidden;
  border-radius: 8px;
  position: relative;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s;
}

.media-item:hover {
  transform: translateY(-2px);
}

.media-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.media-item img:hover {
  transform: scale(1.03);
}

/* 手机端调整 */
@media (max-width: 640px) {
 .media-item {
      height: 100px;
  }
}

/* 整体布局 */
.user-detail-moment-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: var(--bg-color);
  position: relative;
}

/* 头部样式 */
.detail-header {
  left: 240px;
  right: 0;
  width: auto;
  z-index: 100;
  transition: background-color 0.3s;
}

.detail-header:hover {
  background-color: #fcfcfc;
}

.header-content {
  max-width: 600px;
  margin: 0 auto;
  height: 100%;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.title-container {
  text-align: center;
}

h1 {
  font-size: 18px;
  font-weight: 500;
  color: var(--text-color);
}

/* 动态内容区域 */
.moment-detail-container {
  flex: 1;
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
  padding: 0 20px;
  padding-top: 80px;
  padding-bottom: 40px;
}

/* 动态项样式 */
.moment-item {
  background: #fff;
  margin-bottom: 20px;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
}

.moment-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

/* 用户信息 */
.user-info {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  margin-right: 12px;
  object-fit: cover;
  border: 1px solid #f0f0f0;
  cursor: pointer; /* 添加光标样式 */
  transition: transform 0.2s; /* 添加过渡效果 */
}

.user-avatar:hover {
  transform: scale(1.05); /* 鼠标悬停时放大 */
}

.user-details {
  display: flex;
  flex-direction: column;
}

.username {
  font-weight: 500;
  font-size: 16px;
  color: var(--text-color);
  cursor: pointer; /* 添加光标样式 */
  transition: color 0.2s; /* 添加过渡效果 */
}

.username:hover {
  color: var(--primary-color); /* 鼠标悬停时变色 */
}

.post-time {
  font-size: 12px;
  color: var(--light-text-color);
}

/* 动态内容 */
.moment-content {
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-color);
  margin-bottom: 15px;
}

.moment-content :deep(strong) {
  font-weight: 600;
  color: #2d2d2d;
}

/* 图片展示 */
.media-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 12px;
}

/* 点赞和评论区域样式 */
.moment-interaction {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-top: 10px;
  color: var(--light-text-color);
  font-size: 12px;
  gap: 16px;
}
.like-container {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: all 0.2s;
  padding: 3px 6px;
  border-radius: 4px;
}

.like-container:hover {
  background-color: #f5f5f5;
}

.like-container i {
  color: #999;
  transition: color 0.2s;
}
.like-container:hover i {
  color: #07c160;
}

.liked {
  color: #07c160 !important;
}


.comment-container {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: all 0.2s;
  padding: 3px 6px;
  border-radius: 4px;
}

.comment-container:hover {
  background-color: #f5f5f5;
  color: #07c160;
}

.comment-container i {
  color: #999;
}

/* 底部操作区域 */
.moment-footer {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  margin-top: 10px;
  color: var(--light-text-color);
  font-size: 12px;
  margin-bottom: 10px;
}

.time-ago {
  margin-right: var(--spacing-lg);
}

.delete-btn {
  cursor: pointer;
  color: var(--light-text-color);
  transition: all 0.2s;
  padding: 2px 4px;
  border-radius: 3px;
}

.delete-btn:hover {
  color: #f56c6c;
  background-color: #fef0f0;
}

/* 评论列表样式 */
.comments-list {
  list-style-type: none;
  padding: 0;
  margin-top: 15px;
}

.comment-item {
  padding: 15px 0;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  transition: all 0.2s;
}

.comment-item:last-child {
  border-bottom: none;
}

.comment-header {
  display: flex;
  align-items: center;
  width: 100%;
  position: relative;
}

.comment-avatar {
  width: 25px;
  height: 25px;
  border-radius: 50%;
  margin-right: 8px;
  object-fit: cover;
  cursor: pointer; /* 添加光标样式 */
  transition: transform 0.2s; /* 添加过渡效果 */
}

.comment-avatar:hover {
  transform: scale(1.1); /* 鼠标悬停时放大 */
}

.comment-user-details {
  display: flex;
  flex-direction: column;
}

.comment-username {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  cursor: pointer; /* 添加光标样式 */
  transition: color 0.2s; /* 添加过渡效果 */
}

.comment-username:hover {
  color: var(--primary-color); /* 鼠标悬停时变色 */
}

.comment-post-time {
  font-size: 10px;
  color: var(--light-text-color);
}

.comment-content {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background-color: #f9f9f9;
  width: 100%;
  line-height: 1.5;
  font-size: 14px;
}

/* 评论和回复的操作按钮样式 */
.comment-actions, .reply-actions {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  margin-top: 10px;
  font-size: 12px;
  color: var(--light-text-color);
  width: 100%;
}

.comment-actions > div, .reply-actions > div,
.comment-actions > i, .reply-actions > i {
  display: flex;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s;
  padding: 3px 6px;
  border-radius: 4px;
}

/* 调整评论区域互动按钮间距 */
.comment-actions > div:not(:last-child),
.comment-actions > i:not(:last-child) {
  margin-right: 18px; /* 基础间距 */
}

/* 针对点赞按钮单独调整间距 */
.comment-actions .comment-like {
  margin-right: 35px; /* 点赞按钮稍宽，增加间距 */
}

/* 删除按钮靠右对齐 */
.comment-actions .comment-delete-btn {
  margin-left: 18px;
}

/* 回复区域互动按钮样式 */
.reply-actions > div:not(:last-child),
.reply-actions > i:not(:last-child) {
  margin-right: 12px; /* 回复区域间距稍小 */
}

.comment-actions > div:hover, .reply-actions > div:hover,
.comment-actions > i:hover, .reply-actions > i:hover {
  background-color: #f5f5f5;
}

.comment-like, .reply-like {
  color: var(--light-text-color);
}

.comment-like:hover, .reply-like:hover {
  color: var(--primary-color);
}

.comment-reply, .reply-reply {
  color: var(--light-text-color);
}

.comment-reply:hover, .reply-reply:hover {
  color: var(--primary-color);
}

.comment-delete-btn, .reply-delete-btn {
  color: var(--light-text-color);
}

.comment-delete-btn:hover, .reply-delete-btn:hover {
  color: #f56c6c;
  background-color: #fef0f0;
}

/* 回复列表样式 */
.replies-list {
  margin-top: 10px;
  padding-left: 10px;
  border-left: 2px solid #f0f0f0;
}

.reply-item {
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.reply-item:last-child {
  border-bottom: none;
}

.reply-content {
  margin-top: 5px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-color);
}

.reply-time {
  font-size: 10px;
  color: var(--light-text-color);
}

/* ------------------- 评论框和回复框统一样式 ------------------- */
/* 输入区域容器 */
.comment-input-area, .reply-input-area {
  display: flex;
  align-items: center;
  margin-top: 15px;
  width: 100%;
  gap: 12px;
  position: relative;
}

/* 输入框基础样式 */
.comment-input-area input, .reply-input-area input {
  flex: 1;
  height: 44px;
  padding: 0 16px 0 44px;
  border: 2px solid #eaeaea;
  border-radius: 22px;
  background-color: #f8f8f8;
  font-size: 14px;
  color: #333;
  outline: none;
  transition: border-color 0.2s;
}

/* 输入框聚焦状态 */
.comment-input-area input:focus, .reply-input-area input:focus {
  border-color: var(--primary-color);
}

/* 表情图标样式 */
.comment-input-area .emoji-btn, .reply-input-area .emoji-btn {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--light-text-color);
  font-size: 18px;
  cursor: pointer;
  z-index: 1;
  transition: color 0.2s;
}

.comment-input-area .emoji-btn:hover, .reply-input-area .emoji-btn:hover {
  color: var(--primary-color);
}

/* 发送按钮样式 */
.comment-input-area button, .reply-input-area button {
  width: 44px;
  height: 44px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background-color: #eaeaea;
  color: #999;
  font-size: 14px;
  cursor: not-allowed;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 有内容时的发送按钮样式 */
.comment-input-area button:not(:disabled), .reply-input-area button:not(:disabled) {
  background-color: var(--primary-color);
  color: white;
  cursor: pointer;
}

.comment-input-area button:hover:not(:disabled), .reply-input-area button:hover:not(:disabled) {
  background-color: #05a350;
}

/* 发送按钮图标样式 */
.comment-input-area button i, .reply-input-area button i {
  font-size: 16px;
}

/* 回复框特殊调整 */
.reply-input-area {
  margin-top: 8px;
  margin-left: 35px; /* 缩进对齐回复列表 */
}

/* 表情选择器样式 */
.emoji-picker {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  margin-bottom: 10px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  padding: 10px;
  z-index: 10;
  max-height: 240px;
  overflow-y: auto;
}

.emoji-category {
  margin-bottom: 8px;
}

.emoji-category-title {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
  padding-left: 4px;
}

.emoji-grid {
  display: grid;
  grid-template-columns: repeat(15, 1fr);
  gap: 0;
}

.emoji-item {
  padding: 4px;
  text-align: center;
  cursor: pointer;
  transition: transform 0.1s;
}

.emoji-item:hover {
  transform: scale(1.3);
  background-color: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
}

</style>    