<template>
  <div class="moments-page">
    <!-- 左侧用户信息栏 -->
      <div class="user-profile" @click="goToUser">
        <img
          :src="getFullUrl(currentUser.photo) || defaultAvatar"
          class="sidebar-avatar"
        />
        <span class="sidebar-username">{{ currentUser.username }}</span>
    </div>

    <!-- 头部容器 -->
    <div class="moments-header">
      <div class="header-content">
        <div class="title-container">
          <!-- <h1>随便说</h1> -->
          <!-- 新增搜索框 -->
          <div class="search-container mt-4">
            <input 
              v-model="searchQuery" 
              type="text" 
              placeholder="搜索内容或姓名..." 
              class="search-input w-full px-4 py-2 rounded-full border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
              @keyup.enter="handleSearch"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 发布按钮 -->
    <button class="publish-btn" @click="goToPublish">+</button>

    <!-- 动态内容容器 -->
    <div class="moments-container">
      <div class="moments-list">
        <!-- 使用过滤后的动态列表 -->
        <div
          v-for="moment in filteredMoments"
          :key="moment.id"
          class="moment-item"
          @click="goToMomentDetail(moment.id)" 
        >
          <!-- 用户信息 -->
          <div class="user-info">
            <img
              :src="getFullUrl(moment.user.photo) || defaultAvatar"
              class="user-avatar"
            />
            <div class="user-details">
              <span class="username">{{ moment.user.username }}</span>
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
                <source :src="getFullUrl(media.url)" :type="getVideoTypeContent(media.url)">
                您的浏览器不支持视频播放
              </video>
            
                <audio
                v-else-if="media.type === 'audio'"
                :src="getFullUrl(media.url)"
                controls
                :poster="getFullUrl(media.thumbnail)"
              >
                <source :src="getFullUrl(media.url)" :type="getVideoTypeContent(media.url)">
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
            <!-- 删除按钮移至评论图标后，保持space-x-4间距 -->
            <i
              v-if="moment.user_id === currentUser.id"
              class="fa-solid fa-trash-can delete-btn cursor-pointer hover:text-red-500"
              @click.stop="deleteMoment(moment.id)"
            ></i>
          </div>

          <!-- 底部信息 -->
          <div class="moment-footer flex justify-between items-center text-sm text-gray-500">
            <span class="time-ago">{{ getTimeAgo(moment.created_at) }}</span>
          </div>

          <!-- 评论输入框 -->
          <div v-if="moment.showCommentInput" class="comment-input-area flex items-center mt-2">
            <input
              v-model="moment.commentInput"
              type="text"
              placeholder="发表评论..."
              class="flex-1 border border-gray-300 rounded-md p-2 mr-2"
              @keyup.enter="postComment(moment)"
            />
            <button
              @click="postComment(moment)"
              class="px-4 py-2 rounded-md transition-colors duration-200"
              :class="moment.commentInput.trim()? 
                'bg-green-500 text-white hover:bg-green-600' : 
                'bg-gray-300 text-gray-500 cursor-not-allowed'"
              :disabled="!moment.commentInput.trim()"
            >
              发布
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
                  @click="goToUserProfile(comment.comment_user_id)"
                />
                <div class="comment-user-details">
                  <span class="comment-username" @click="goToUserProfile(comment.comment_user_id)">{{ comment.comment_user_name }}</span>
                  <span class="comment-post-time">{{ formatTime(comment.created_at) }}</span>
                </div>
              </div>
              
              <div class="comment-content mt-1 ml-8 text-gray-600 text-sm">
                {{ comment.comment }}
              </div>

              <!-- 回复操作 -->
              <div class="comment-actions flex justify-end space-x-3 mt-1 text-xs">
                <div class="comment-like flex items-center space-x-1" @click="likeComment(moment.id, index)">
                  <i class="fa-solid fa-thumbs-up" :class="{ 'liked': comment.isLiked }"></i>
                  <span>{{ comment.likes }}</span>
                </div>
                <div class="comment-reply flex items-center space-x-1" @click="toggleReplyInput(comment)">
                  <i class="fa-solid fa-comment"></i>
                  <span>{{ comment.replies?.length || 0 }}</span>
                </div>
              </div>

              <!-- 回复输入框 -->
              <div v-if="comment.showReplyInput" class="reply-input-area flex items-center mt-2 ml-8">
                <input
                  v-model="comment.replyInput"
                  type="text"
                  placeholder="回复评论..."
                  class="flex-1 border border-gray-300 rounded-md p-2 mr-2 text-sm"
                  @keyup.enter="postReply(moment, comment)"
                />
                <button
                  @click="postReply(moment, comment)"
                  class="px-3 py-1.5 rounded-md transition-colors duration-200 text-sm"
                  :class="comment.replyInput.trim()? 
                    'bg-green-500 text-white hover:bg-green-600' : 
                    'bg-gray-300 text-gray-500 cursor-not-allowed'"
                  :disabled="!comment.replyInput.trim()"
                >
                  发送
                </button>
              </div>

              <!-- 回复列表 -->
              <div v-if="comment.replies?.length" class="replies-list ml-8 mt-2">
                <div 
                  v-for="(reply, replyIndex) in comment.replies"
                  :key="replyIndex"
                  class="reply-item py-2 border-t border-gray-100"
                >
                  <div class="flex items-center space-x-2">
                    <img
                      :src="getFullUrl(reply.comment_user_photo) || defaultAvatar"
                      class="w-5 h-5 rounded-full"
                    />
                    <span class="text-sm font-medium">{{ reply.comment_user_name }}</span>
                    <span class="text-xs text-gray-500">{{ formatTime(reply.created_at) }}</span>
                  </div>
                  <div class="reply-content ml-7 text-gray-600 text-sm">
                    {{ reply.comment }}
                  </div>
                </div>
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
      </div>
      
      <div v-if="filteredMoments.length === 0 && searchQuery.value" class="no-results-message text-center py-8">
        没有找到匹配的内容
      </div>
      
      <div v-if="noMore && !searchQuery.value" class="no-more-message">
        没有更多动态了
      </div>
    </div>
  </div>
</template>

<script>
// 脚本部分与之前一致，无修改
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useStore } from 'vuex'
import axios from 'axios'
import DOMPurify from 'dompurify'
import defaultAvatar from '@/assets/default-avatar.png'
import { API_CONFIG } from '@/config/config'
import { ElMessage } from 'element-plus'

export default {
  setup() {
    const router = useRouter()
    const store = useStore()
    const moments = ref([])
    const loading = ref(false)
    const noMore = ref(false)
    const lastId = ref(null)
    const pageSize = 10
    
    // 新增搜索相关变量
    const searchQuery = ref('')

    // 计算属性：过滤后的动态列表
    const filteredMoments = computed(() => {
      if (!searchQuery.value) {
        return moments.value
      }
      
      const query = searchQuery.value.toLowerCase()
      return moments.value.filter(moment => 
        moment.content.toLowerCase().includes(query) || 
        moment.user.username.toLowerCase().includes(query)
      )
    })

    // 用户方法
    const currentUser = computed(() => store.state.user || {})
    const goToUser = () => router.push('/user/dashboard')
    const goToUserProfile = (userId) => router.push(`/user/${userId}`)
    const goToPublish = () => router.push('/publish')
   
    const goToMomentDetail = (momentId) => {
      router.push(`/moment/${momentId}`) // 跳转到详情页面
    }
    // 工具方法
    const getFullUrl = (path) => {
      if (!path || path === defaultAvatar) return path
      return path.startsWith('http') ? path : `${API_CONFIG.BASE_URL}${path}`
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

const getVideoTypeContent = (url) => {
  if (!url) return 'application/octet-stream';
  
  const lowerUrl = url.toLowerCase();
  const ext = lowerUrl.split('.').pop(); // 获取文件后缀
  
  // 通过映射表获取类型，无匹配时返回通用类型
  return mediaTypeMap[ext] || 'application/octet-stream';
};
  //   const getVideoTypeContent = (url) => {
  // // if (!url) return 'video/mp4';
  
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
  
  // return 'video/mp4'; // 默认返回视频类型
  //   }
    
    
    const openImagePreview = (url) => {
      window.open(url, '_blank')
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


// 动态加载
const fetchMoments = async () => {
  if (loading.value || noMore.value) return;
  loading.value = true;

  try {
    const params = { limit: pageSize, last_id: lastId.value };
    const response = await axios.get(`${API_CONFIG.BASE_URL}/article/moments`, {
      headers: { Authorization: `Bearer ${store.state.token}` },
      params
    });

    // console.log("原始响应数据：", response.data);

    // 处理加密数据 - 使用Promise.all处理异步解密
    const newMoments = await Promise.all(
      response.data.map(async item => {
        console.log( item);
        
        
        try {
          
          // 确保解密后的数据包含所有必要字段
          const moment = {
            ...item,
            id: item.id || `temp_id_${Date.now()}`,
            content: item.content || '',
            user: item.user || {},
            create_time: item.create_time || Date.now(),
            like_users: item.like_users || [],
            comments: item.comments || []
          };
          
          return {
            ...moment,
            showCommentInput: false,
            commentInput: '',
            comments: moment.comments.map(comment => ({
              ...comment,
              showReplyInput: false,
              replyInput: '',
              replies: comment.replies || []
            })),
            showAllComments: false,
            isLiked: moment.like_users?.includes(currentUser.value.id) || false
          };
        } catch (Error) {
          console.error('报错了',Error );
          return null;
        }
      })
    );

    // 过滤掉解密失败的数据
    const validMoments = newMoments.filter(moment => moment !== null);
    // console.log("最终处理后的新动态：", validMoments);
    
    // 检查是否有新数据
    if (validMoments.length > 0) {
      moments.value = [...moments.value, ...validMoments];
      lastId.value = validMoments[validMoments.length - 1]?.id;
      noMore.value = validMoments.length < pageSize;
    } else {
      noMore.value = true;
    }
  } catch (error) {
    console.error('获取动态失败:', error);
    // ElMessage.error('加载动态失败');
  } finally {
    loading.value = false;
  }
};
    // const fetchMoments = async () => {
    //   if (loading.value || noMore.value) return
    //   loading.value = true

    //   try {
    //     const params = { limit: pageSize, last_id: lastId.value }
    //     const response = await axios.get(`${API_CONFIG.BASE_URL}/article/moments`, {
    //       headers: { Authorization: `Bearer ${store.state.token}` },
    //       params
    //     })

    //     const newMoments = response.data.map(moment => ({

    //       ...moment,
    //       showCommentInput: false,
    //       commentInput: '',
    //       comments: (moment.comments || []).map(comment => ({
    //         ...comment,
    //         showReplyInput: false,
    //         replyInput: '',
    //         replies: comment.replies || []
    //       })),
    //       showAllComments: false,
    //       isLiked: moment.like_users?.includes(currentUser.value.id) || false
    //     }))

    //     moments.value = [...moments.value, ...newMoments]
    //     lastId.value = newMoments[newMoments.length - 1]?.id
    //     noMore.value = newMoments.length < pageSize
    //   } catch (error) {
    //     console.error('获取动态失败:', error)
    //     ElMessage.error('加载动态失败')
    //   } finally {
    //     loading.value = false
    //   }
    // };

    // 搜索处理函数
    const handleSearch = () => {
      if (searchQuery.value) {
        // 搜索时重置加载状态
        lastId.value = null
        noMore.value = false
      }
    }

    // 互动功能
    const toggleCommentInput = (moment) => {
      moment.showCommentInput = !moment.showCommentInput
      moment.commentInput = ''
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

        if (response.data.success) {
          // 在数组开头添加新评论
          moment.comments.unshift({
            id: response.data.id,
            comment: moment.commentInput,
            created_at: new Date().toISOString(),
            comment_user_name: currentUser.value.username,
            comment_user_photo: currentUser.value.photo,
            likes: 0,
            isLiked: false,
            replies: []
          })
          
          // 更新评论数量
          moment.stats.comments += 1
          
          // 清空输入框并关闭
          moment.commentInput = ''
          moment.showCommentInput = false
          
          // ElMessage.success('评论发布成功')
        }
      } catch (error) {
        console.error('评论失败:', error)
        // ElMessage.error('评论发布失败')
      }
    }

    const toggleReplyInput = (comment) => {
      comment.showReplyInput = !comment.showReplyInput
      comment.replyInput = ''
    }

    const postReply = async (moment, comment) => {
      if (!comment.replyInput.trim()) return

      try {
        const response = await axios.post(
          `${API_CONFIG.BASE_URL}/article/post_reply`,
          {
            moment_id: moment.id,
            parent_comment_id: comment.id,
            comment: comment.replyInput,
            comment_user_id: currentUser.value.id
          },
          { headers: { Authorization: `Bearer ${store.state.token}` } }
        )

        if (response.data.success) {
          comment.replies.push({
           ...response.data.reply,
            comment_user_name: currentUser.value.username,
            comment_user_photo: currentUser.value.photo
          })
          comment.replyInput = ''
          comment.showReplyInput = false
          // ElMessage.success('回复成功')
        }
      } catch (error) {
        console.error('回复失败:', error)
        // ElMessage.error('回复失败')
      }
    }

// 点赞功能
    const likeMoment = async (momentId) => {
          const targetMoment = moments.value.find(moment => moment.id === momentId)
          if (!targetMoment) return

          // 保存原始状态用于回滚
          const originalIsLiked = targetMoment.isLiked
          const originalLikes = targetMoment.stats.likes
          
          try {
            // 立即更新UI状态
            targetMoment.isLiked = !targetMoment.isLiked
            targetMoment.stats.likes += targetMoment.isLiked ? 1 : -1

            const response = await axios.post(`${API_CONFIG.BASE_URL}/article/like_moment`, {
              moment_id: momentId,
              user_id: currentUser.value.id,
              is_like: targetMoment.isLiked
            }, {
              headers: {
                Authorization: `Bearer ${store.state.token}`
              },
              timeout: 5000 // 增加超时控制
            })

            if (response.data.success) {
              // 检查 stats 是否存在，如果不存在则初始化
              if (!targetMoment.stats) {
                    targetMoment.stats = { likes: 0 };
                }
                
                // 更新前端状态
                targetMoment.isLiked = response.data.likes > targetMoment.stats.likes;
                targetMoment.stats.likes = response.data.likes;
                // ElMessage.success(targetMoment.isLiked ? '点赞成功' : '已取消点赞');

              // 精确同步后端数据
              targetMoment.isLiked = response.data.is_liked
              targetMoment.stats.likes = response.data.likes_count
              
              // 更新like_users列表
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
            // 回滚状态
            targetMoment.isLiked = originalIsLiked
            targetMoment.stats.likes = originalLikes
            
            console.error('点赞操作失败:', error)
            // ElMessage.error(`操作失败: ${error.response?.data?.msg || '网络错误'}`)
          }
        }

 

    const likeComment = async (momentId, commentIndex) => {
      const moment = moments.value.find(m => m.id === momentId)
      const comment = moment?.comments[commentIndex]
      if (!comment) return

      try {
        const response = await axios.post(
          `${API_CONFIG.BASE_URL}/article/like_comment`,
          { comment_id: comment.id, user_id: currentUser.value.id },
          { headers: { Authorization: `Bearer ${store.state.token}` } }
        )

        comment.isLiked = response.data.is_liked
        comment.likes = response.data.likes_count
      } catch (error) {
        console.error('点赞失败:', error)
      }
    }

    const deleteMoment = async (momentId) => {
      try {
        await axios.post(
          `${API_CONFIG.BASE_URL}/article/delete/moment`,
          { moment_id: momentId },
          { headers: { Authorization: `Bearer ${store.state.token}` } }
        )
        moments.value = moments.value.filter(m => m.id!== momentId)
        // ElMessage.success('删除成功')
      } catch (error) {
        console.error('删除失败:', error)
        ElMessage.error('删除失败')
      }
    }

    // 辅助函数
    const visibleComments = (moment) => {
      return moment.showAllComments? 
        moment.comments : 
        moment.comments.slice(0, 3)
    }

    // 生命周期
    onMounted(() => {
      fetchMoments()
      window.addEventListener('scroll', handleScroll)
    })

    onUnmounted(() => {
      window.removeEventListener('scroll', handleScroll)
    })

    const handleScroll = () => {
      if (searchQuery.value) return // 搜索时不加载更多
      
      const { scrollTop, scrollHeight, clientHeight } = document.documentElement
      if (scrollTop + clientHeight >= scrollHeight - 100 &&!loading.value) {
        fetchMoments()
      }
    }

    return {
      moments,
      currentUser,
      noMore,
      loading,
      visibleComments,
      getFullUrl,
      formatTime,
      getTimeAgo,
      sanitizeHtml,
      goToUser,
      goToUserProfile,
      goToPublish,
      toggleCommentInput,
      postComment,
      toggleReplyInput,
      postReply,
      openImagePreview,
      getVideoTypeContent,
      goToMomentDetail,
      likeMoment,
      likeComment,
      deleteMoment,
      defaultAvatar,
      searchQuery,
      filteredMoments,
      handleSearch
    }
  }
}
</script>

<style scoped>


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

/* 头像样式 - 调整为合适大小 */
.sidebar-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%; /* 圆形头像 */
  border: 2px solid #07c160;
  padding: 1px;
  align-items: center;
  object-fit: cover; /* 图片自适应填充 */
  flex-shrink: 0; /* 防止头像被压缩 */
}

/* 用户名样式 */
.sidebar-username {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin: 0; /* 清除可能的外边距 */
  flex-shrink: 1; /* 允许名字在空间不足时收缩 */
}

/* 新增视频相关样式 */
.video-container {
  position: relative;
  padding-top: 56.25%; /* 16:9 宽高比 */
}

video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 4px;
  background: #000;
}

/* 调整媒体项高度 */
.media-item {
  height: 120px; /* 统一图片和视频高度 */
  overflow: hidden;
}

/* 手机端调整 */
@media (max-width: 640px) {
 .media-item {
      height: 100px;
  }
}

/* 整体布局 */
.moments-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #f8f8f8;
  position: relative;
}

/* 头部样式 */
.moments-header {
  left: 240px; /* 给侧边栏留出空间 */
  right: 0;
  width: auto;
}

.header-content {
  max-width: 600px;
  margin: 0 auto;
  height: 100%;
  padding: 0 20px;
  display: flex;
  flex-direction: column; /* 改为垂直布局 */
  align-items: center;
  justify-content: center;
  position: relative;
}

.title-container {
  text-align: center;
  width: 100%; /* 占满宽度 */
}

h1 {
  font-size: 18px;
  font-weight: 500;
  color: #333;
  margin-bottom: 0; /* 减少标题与搜索框的间距 */
}

/* 新增搜索框样式 - 改为椭圆形 */
.search-container {
  width: 100%;
  max-width: 500px; /* 限制搜索框最大宽度 */
  margin-top: 10px; /* 调整搜索框与标题的间距 */
}

.search-input {
  width: 100%;
  padding: 8px 15px;
  font-size: 14px;
  border: 1px solid #ddd;
  border-radius: 50px; /* 椭圆形边框 */
  box-sizing: border-box;
  transition: border-color 0.3s, box-shadow 0.3s;
  background-color: #fff;
}

.search-input:focus {
  border-color: #07c160;
  box-shadow: 0 0 0 2px rgba(7, 193, 96, 0.2);
  outline: none;
}

/* 发布按钮 */
.publish-btn {
  position: fixed;
  right: 20px;
  top: 12px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #07c160;
  color: white;
  border: none;
  cursor: pointer;
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  z-index: 200;
  transition: transform 0.2s;
}

.publish-btn:hover {
  transform: scale(1.05);
}

/* 内容区域 */
.moments-container {
  flex: 1;
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
  padding: 0 20px;
}

.moments-list {
  padding: 20px 0;
}

/* 动态项样式 */
.moment-item {
  background: #fff;
  margin-bottom: 20px;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
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
}

.user-details {
  display: flex;
  flex-direction: column;
}

.username {
  font-weight: 500;
  font-size: 16px;
}

.post-time {
  font-size: 12px;
  color: #999;
}

/* 动态内容 */
.moment-content {
  font-size: 16px;
  line-height: 1.6;
  color: #333;
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

.media-item img {
  width: 100%;
  height: 120px;
  object-fit: cover;
  border-radius: 4px;
}

/* 点赞和评论区域样式 */
.moment-interaction {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-top: 10px;
  color: #999;
  font-size: 12px;
  gap: 16px; /* 保持互动元素间距一致 */
}

.like-container {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: color 0.2s;
}

.like-container:hover {
  color: #07c160;
}

.like-container i {
  color: #999;
}

.liked {
  color: #07c160 !important;
}

.comment-container {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: color 0.2s;
}

.comment-container:hover {
  color: #07c160;
}

.comment-container i {
  color: #999;
}

/* 优化删除按钮样式，保持与其他元素间距一致 */
.delete-btn {
  color: #999;
  font-size: 16px;
  transition: all 0.2s;
  /* 移除原有边距，通过flex容器的space-x-4保持间距 */
}

.delete-btn:hover {
  color: #f56c6c;
}

/* 底部操作区域 */
.moment-footer {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  margin-top: 10px;
  color: #999;
  font-size: 12px;
  margin-bottom: 10px;
}

.time-ago {
  margin-right: var(--spacing-lg);
}

/* 响应式调整 */
@media (max-width: 640px) {
 .publish-btn {
      right: 10px;
      top: 10px;
      width: 36px;
      height: 36px;
      font-size: 20px;
  }

  h1 {
      font-size: 16px;
  }

 .moments-container {
      padding: 0 15px;
  }

 .moment-item {
      padding: 15px;
  }

 .comment-input-container input {
      height: 26px;
      padding: 0 8px;
  }

 .comment-input-container button {
      height: 26px;
      padding: 0 12px;
  }
  
  /* 移动端搜索框样式调整 */
  .search-container {
    margin-top: 8px;
  }
  
  .search-input {
    padding: 6px 12px;
    font-size: 13px;
  }
}

.no-more-message {
  text-align: center;
  color: #999;
  padding: 10px 0;
}

/* 新增：搜索无结果提示 */
.no-results-message {
  text-align: center;
  color: #999;
  padding: 20px 0;
  font-size: 14px;
}

/* 评论列表样式 */
.comments-list {
  list-style-type: none;
  padding: 0;
}

.comment-item {
  padding: 15px 0;
  border-bottom: 1px solid #eaeaea; /* 新增：添加评论之间的分割线 */
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
}

.comment-item:last-child {
  border-bottom: none;
}

.comment-header {
  display: flex;
  align-items: center;
  width: 100%;
}

.comment-avatar {
  width: 25px; /* 缩小评论头像 */
  height: 25px;
  border-radius: 50%;
  margin-right: 8px;
}

.comment-user-details {
  display: flex;
  flex-direction: column;
}

.comment-username {
  font-size: 14px; /* 缩小评论用户名 */
  font-weight: 500;
}

.comment-post-time {
  font-size: 10px;
  color: #999;
}

.comment-content-wrapper {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid #eaeaea;
  border-radius: 6px;
  background-color: #f9f9f9;
  width: 100%;
}

.comment-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-top: 10px;
  font-size: 12px;
  color: #666;
  width: 100%;
}

.comment-like {
  display: flex;
  align-items: center;
  margin-right: 20px; /* 增加点赞和评论之间的间距 */
  cursor: pointer;
}

.comment-comment {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.comment-actions i {
  margin-right: 5px;
}

.show-more-comments {
  margin-top: 10px;
  color: #007bff;
  cursor: pointer;
}
/* 保持原有样式，移除取消按钮相关样式 */
.comment-input-area button {
  transition: background-color 0.2s, transform 0.1s;
}

.comment-input-area button:active {
  transform: scale(0.98);
}

/* 优化移动端输入框体验 */
@media (max-width: 640px) {
  .comment-input-area {
    flex-wrap: wrap;
  }
  
  .comment-input-area input {
    width: 100%;
    margin-bottom: 8px;
  }
  
  .comment-input-area button {
    width: 100%;
  }
/* 头部样式调整 */
.moments-header {
  position: sticky;
  top: 0;
  background: #fff;
  padding: 15px 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 100;
  width: 100%;
}

.header-content {
  max-width: 600px;
  margin: 0 auto;
  padding: 0 20px;
}

.title-container {
  position: relative;
  text-align: center;
  width: 100%;
}

/* 圆形头像样式，宽高一致并设置圆角 50% */
.header-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  margin-bottom: 15px;
  border: 2px solid var(--primary-color);
  padding: 3px;
  object-fit: cover;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

/* 用户名样式，居左显示 */
.header-username {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  white-space: nowrap; /* 防止用户名换行 */
}

/* 标题样式调整 */
h1 {
  font-size: 18px;
  font-weight: 500;
  color: #333;
  margin: 0 auto;
  display: inline-block;
}

/* 搜索框样式调整 */
.search-container {
  width: 100%;
  max-width: 500px; /* 限制搜索框最大宽度 */
  margin-top: 10px; /* 调整搜索框与标题的间距 */
}

/* 发布按钮位置调整 */
.publish-btn {
  position: fixed;
  right: 20px;
  top: 70px; /* 下移以避免与头部重叠 */
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #07c160;
  color: white;
  border: none;
  cursor: pointer;
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  z-index: 200;
  transition: transform 0.2s;
}

.publish-btn:hover {
  transform: scale(1.05);
}

/* 内容区域调整 */
.moments-container {
  flex: 1;
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
  padding: 20px;
  margin-top: 0; /* 移除顶部间距 */
}


/* 响应式调整 */
@media (max-width: 640px) {
  .header-content {
    padding: 0 15px;
  }
  
  h1 {
    font-size: 16px;
  }
  
  .publish-btn {
    right: 15px;
    top: 65px;
    width: 36px;
    height: 36px;
    font-size: 20px;
  }
  
  .moments-container {
    padding: 15px;
  }
  

  /* 在小屏幕上隐藏用户名 */
@media (max-width: 480px) {
  .header-avatar {
    width: 24px;
    height: 24px;
  }
  
  .header-username {
    font-size: 12px;
    /* 小屏幕下仍显示用户名，仅在极端情况下隐藏 */
    /* display: none; */
  }
}

@media (max-width: 480px) {
  .header-avatar {
    width: 36px;        /* 在中等屏幕上稍小 */
    height: 36px;
    border-width: 1.5px;
  }
}

    }
} 
</style>