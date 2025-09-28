<template>
  <div class="user-page">
    <header class="header">
      <div class="header-left">
        <!-- 点击头像跳转到用户详情页 -->
        <div class="user-info" @click="goToUserDetail">
          <img :src="avatarUrl" alt="头像" class="avatar" />
          <span class="username">{{ displayName }}</span>
        </div>
      </div>
      <!-- <div class="header-right">
        <button @click="logout" class="logout-button">退出登录</button>
      </div> -->
    </header>

    <div class="main-layout"> 
      <!-- <aside class="sidebar">
        <ul class="menu">
          <li class="menu-item">
            <router-link to="/user/dashboard" class="menu-link">仪表盘</router-link>
          </li>
        
          <li class="menu-item">
            <router-link to="/moments" class="menu-link">朋友圈</router-link>
          </li>

          <li class="menu-item">
             用户信息 --> 
            <!-- <div @click="toggleUserInfo" class="menu-title">
              用户信息
              <span class="arrow">{{ isUserInfoOpen ? '▼' : '▶' }}</span>
            </div>
            用户信息子目录
             <ul v-if="isUserInfoOpen" class="sub-menu">
              <li class="sub-menu-item">
                <router-link to="/user/userinfo/userlist" class="sub-menu-link">用户列表</router-link>
              </li>
              <li class="sub-menu-item2">
                <router-link to="/user/bigdatauser/userlist" class="sub-menu-link">大数据用户</router-link>
              </li>
            </ul>
          </li>
        </ul>
      </aside> -->

      <main class="main-content">
        <!-- 新增的导航标签 -->
        <div class="content-tabs">
          <div 
            class="tab" 
            :class="{ 'active': activeTab === 'published' }"
            @click="switchTab('published')"
          >
            我发布的
          </div>
          <div 
            class="tab" 
            :class="{ 'active': activeTab === 'liked' }"
            @click="switchTab('liked')"
          >
            我喜欢的
          </div>
        </div>
        
        <!-- 内容区域 -->
        <div class="content-container">
          <div v-if="activeTab === 'published'" class="published-content">
            <!-- 我发布的内容列表 -->
            <div 
              v-for="moment in publishedMoments" 
              :key="moment.id" 
              class="moment-item"
              @click="goToMomentDetail(moment.id)"
            >
              <div class="user-info">
                <img :src="getFullUrl(moment.user.photo) || defaultAvatar" class="user-avatar" />
                <div class="user-details">
                  <span class="username">{{ moment.user.username }}</span>
                  <span class="post-time">{{ formatTime(moment.created_at) }}</span>
                </div>
              </div>
              
              <div class="moment-content" v-html="sanitizeHtml(moment.content)"></div>
              
              <div v-if="moment.media?.length" class="media-grid">
                <div
                  v-for="(media, index) in moment.media"
                  :key="index"
                  class="media-item"
                >
                  <img
                    v-if="media.type === 'image'"
                    :src="getFullUrl(media.url)"
                    @click.stop="openImagePreview(getFullUrl(media.url))"
                    class="previewable-image"
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
              
              <div class="moment-footer">
                <span class="time-ago">{{ getTimeAgo(moment.created_at) }}</span>
              </div>
              
              <!-- 互动区域 - 调整删除按钮位置到评论图标后 -->
              <div class="moment-interaction flex justify-end space-x-4">
                <div class="like-container flex items-center space-x-1 cursor-pointer" @click.stop="likeMoment(moment.id)">
                  <i
                    class="fa-solid fa-thumbs-up"
                    :class="{ 'liked': moment.isLiked }"
                  ></i>
                  <span>{{ moment.stats?.likes || 0 }}</span>
                </div>
                <div class="comment-container flex items-center space-x-1 cursor-pointer" @click.stop="goToMomentDetail(moment.id)">
                  <i class="fa-solid fa-comment"></i>
                  <span>{{ moment.stats?.comments || 0 }}</span>
                </div>
                <!-- 删除按钮 - 移到评论图标右侧，保持space-x-4间距 -->
                <i
                  v-if="moment.user_id === currentUser.id"
                  class="fa-solid fa-trash-can delete-btn cursor-pointer hover:text-red-500 transition-colors"
                  @click.stop="deleteMoment(moment.id, 'published')"
                ></i>
              </div>
            </div>
          </div>
          
          <div v-if="activeTab === 'liked'" class="liked-content">
            <!-- 我喜欢的内容列表 -->
            <div 
              v-for="moment in likedMoments" 
              :key="moment.id" 
              class="moment-item"
              @click="goToMomentDetail(moment.id)"
            >
              <div class="user-info">
                <img :src="getFullUrl(moment.user.photo) || defaultAvatar" class="user-avatar" />
                <div class="user-details">
                  <span class="username">{{ moment.user.username }}</span>
                  <span class="post-time">{{ formatTime(moment.created_at) }}</span>
                </div>
              </div>
              
              <div class="moment-content" v-html="sanitizeHtml(moment.content)"></div>
              
              <div v-if="moment.media?.length" class="media-grid">
                <div
                  v-for="(media, index) in moment.media"
                  :key="index"
                  class="media-item"
                >
                  <img
                    v-if="media.type === 'image'"
                    :src="getFullUrl(media.url)"
                    @click.stop="openImagePreview(getFullUrl(media.url))"
                    class="previewable-image"
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
              
              <div class="moment-footer">
                <span class="time-ago">{{ getTimeAgo(moment.created_at) }}</span>
              </div>
              
              <!-- 互动区域 - 调整删除按钮位置到评论图标后 -->
              <div class="moment-interaction flex justify-end space-x-4">
                <div class="like-container flex items-center space-x-1 cursor-pointer" @click.stop="likeMoment(moment.id)">
                  <i
                    class="fa-solid fa-thumbs-up"
                    :class="{ 'liked': moment.isLiked }"
                  ></i>
                  <span>{{ moment.stats?.likes || 0 }}</span>
                </div>
                <div class="comment-container flex items-center space-x-1 cursor-pointer" @click.stop="goToMomentDetail(moment.id)">
                  <i class="fa-solid fa-comment"></i>
                  <span>{{ moment.stats?.comments || 0 }}</span>
                </div>
                <!-- 删除按钮 - 移到评论图标右侧，保持space-x-4间距 -->
                <i
                  v-if="moment.user_id === currentUser.id"
                  class="fa-solid fa-trash-can delete-btn cursor-pointer hover:text-red-500 transition-colors"
                  @click.stop="deleteMoment(moment.id, 'liked')"
                ></i>
              </div>
            </div>
            
            <!-- 加载提示 -->
            <div v-if="isLoadingLiked && likedMoments.length > 0" class="loading-tip">
              <i class="el-icon-loading"></i> 加载中...
            </div>
            
            <!-- 没有更多数据提示 -->
            <div v-if="noMoreLiked && likedMoments.length > 0" class="no-more-tip">
              没有更多内容了
            </div>
          </div>
        </div>
        
        <!-- 图片预览模态框 -->
        <div v-if="showImagePreview" class="image-preview-modal" @click="closeImagePreview">
          <div class="image-preview-content">
            <button class="close-preview" @click.stop="closeImagePreview">
              <i class="fa fa-times"></i>
            </button>
            <img :src="currentPreviewImage" alt="预览图片" class="preview-image" />
          </div>
        </div>
        
        <router-view></router-view>
      </main>
    </div>
  </div>
</template>

<script>
// 脚本部分与之前一致，无修改
import { computed, onUnmounted, onMounted, ref } from 'vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';
import defaultAvatar from '@/assets/default-avatar.png';
import { API_CONFIG } from '@/config/config';
import axios from 'axios';
import DOMPurify from 'dompurify';
import { ElMessage } from 'element-plus';

export default {
  name: 'UserPage',
  setup() {
    const store = useStore();
    const router = useRouter();
    const isUserInfoOpen = ref(false);
    const activeTab = ref('published');
    const publishedMoments = ref([]);
    const likedMoments = ref([]);
    const currentUser = computed(() => store.state.user || {});

    const showImagePreview = ref(false);
    const currentPreviewImage = ref('');

    const lastPublishedId = ref(null);
    const noMorePublished = ref(false);
    const isLoadingPublished = ref(false);
    const publishedPageSize = 10;

    const lastLikedId = ref(null);
    const noMoreLiked = ref(false);
    const likedPageSize = 10;
    const isLoadingLiked = ref(false);

    const user = computed(() => store.state.user);
    const displayName = computed(() => user.value?.username || user.value?.phone || user.value?.email || '未登录');

        // 加密函数

    const avatarUrl = computed(() => {
      if (user.value?.photo) {
        return `${API_CONFIG.BASE_URL}${user.value.photo}`;
      }
      return defaultAvatar;
    });

    const getFullUrl = (path) => {
      if (!path || path === defaultAvatar) return path;
      return path.startsWith('http') ? path : `${API_CONFIG.BASE_URL}${path}`;
    };

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
    const formatTime = (timestamp) => {
      const date = new Date(timestamp);
      return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-` +
             `${date.getDate().toString().padStart(2, '0')} ` +
             `${date.getHours().toString().padStart(2, '0')}:` +
             `${date.getMinutes().toString().padStart(2, '0')}`;
    };

    const getTimeAgo = (timestamp) => {
      const now = Date.now();
      const diff = now - new Date(timestamp).getTime();
      const minutes = Math.floor(diff / 60000);
      const hours = Math.floor(minutes / 60);
      const days = Math.floor(hours / 24);

      if (minutes < 1) return '刚刚';
      if (minutes < 60) return `${minutes}分钟前`;
      if (hours < 24) return `${hours}小时前`;
      return `${days}天前`;
    };

    const sanitizeHtml = (html) => DOMPurify.sanitize(html);

    const openImagePreview = (url) => {
      currentPreviewImage.value = url;
      showImagePreview.value = true;
      document.body.style.overflow = 'hidden';
    };

    const closeImagePreview = () => {
      showImagePreview.value = false;
      document.body.style.overflow = '';
    };

    const goToMomentDetail = (momentId) => {
      router.push(`/moment/${momentId}`);
    };

const fetchPublishedMoments = async (refresh = false) => {
  if (isLoadingPublished.value && !refresh) return;
  
  try {
    isLoadingPublished.value = true;
    
    if (refresh) {
      lastPublishedId.value = null;
      noMorePublished.value = false;
      publishedMoments.value = [];
    }
    
    if (noMorePublished.value && !refresh) return;
    
    const params = {
      limit: publishedPageSize
    };
    
    if (!refresh && lastPublishedId.value) {
      params.last_id = lastPublishedId.value;
    }
    
    const response = await axios.get(`${API_CONFIG.BASE_URL}/article/user_moments`, {
      headers: { Authorization: `Bearer ${store.state.token}` },
      params
    });
    

    const newMoments = await Promise.all(
      response.data.map(async item => {

        try {
  
   
          const moment = {
            ...item,
            id: item.id || `temp_id_${Date.now()}`,
            content: item.content || '',
            user: item.user || {},
            create_time: item.create_time || Date.now(),
            like_users: item.like_users || [],
            comments: item.comments || [],
            stats: {
              likes: item.stats?.likes || 0,
              comments: item.stats?.comments || 0
            }
          };
          
          // 处理解密后的动态数据
          return {
            ...moment,
            showCommentInput: false,
            commentInput: '',
            showAllComments: false,
            isLiked: moment.like_users?.includes(user.value.id) || false,
            comments: moment.comments.map(comment => ({
              ...comment,
              showReplyInput: false,
              replyInput: '',
              replies: comment.replies || []
            }))
          };
        } catch (tError) {
          console.error('出错：', Error);
          return null;
        }
      })
    );
    
    // 过滤掉解密失败的数据
    const validMoments = newMoments.filter(moment => moment !== null);
    
    if (refresh) {
      publishedMoments.value = validMoments;
    } else {
      publishedMoments.value = [...publishedMoments.value, ...validMoments];
    }
    
    if (validMoments.length > 0) {
      lastPublishedId.value = validMoments[validMoments.length - 1].id;
    }
    noMorePublished.value = validMoments.length < publishedPageSize;
    
  } catch (error) {
    console.error('获取发布内容失败:', error);
    ElMessage.error('获取发布内容失败');
  } finally {
    isLoadingPublished.value = false;
  }
};
const fetchLikedMoments = async (refresh = false) => {
  if (isLoadingLiked.value && !refresh) return;
  
  try {
    isLoadingLiked.value = true;
    
    if (refresh) {
      lastLikedId.value = null;
      noMoreLiked.value = false;
      likedMoments.value = [];
    }
    
    if (noMoreLiked.value && !refresh) return;
    
    const params = {
      limit: likedPageSize
    };
    
    if (!refresh && lastLikedId.value) {
      params.last_id = lastLikedId.value;
    }
    
    const response = await axios.get(`${API_CONFIG.BASE_URL}/article/liked_moments`, {
      headers: { Authorization: `Bearer ${store.state.token}` },
      params
    });
    
    // 处理加密数据 - 使用Promise.all处理异步解密
    const newMoments = await Promise.all(
      response.data.map(async item => {
        
        try {
          
          const moment = {
            ...item,
            id: item.id || `temp_id_${Date.now()}`,
            content: item.content || '',
            user: item.user || {},
            create_time: item.create_time || Date.now(),
            like_users: item.like_users || [],
            comments: item.comments || [],
            stats: {
              likes: item.stats?.likes || 0,
              comments: item.stats?.comments || 0
            }
          };
          
          // 处理解密后的动态数据
          return {
            ...moment,
            showCommentInput: false,
            commentInput: '',
            showAllComments: false,
            // 对于"我喜欢的"列表，默认设置为已点赞
            isLiked: true,
            comments: moment.comments.map(comment => ({
              ...comment,
              showReplyInput: false,
              replyInput: '',
              replies: comment.replies || []
            }))
          };
        } catch (Error) {
          console.error('出错了', Error);
          return null;
        }
      })
    );
    
    // 过滤掉解密失败的数据
    const validMoments = newMoments.filter(moment => moment !== null);
    
    if (refresh) {
      likedMoments.value = validMoments;
    } else {
      likedMoments.value = [...likedMoments.value, ...validMoments];
    }
    
    if (validMoments.length > 0) {
      lastLikedId.value = validMoments[validMoments.length - 1].id;
    }
    noMoreLiked.value = validMoments.length < likedPageSize;
    
  } catch (error) {
    console.error('获取喜欢内容失败:', error);
    ElMessage.error('获取喜欢内容失败');
  } finally {
    isLoadingLiked.value = false;
  }
};
    // const fetchPublishedMoments = async (refresh = false) => {
    //   if (isLoadingPublished.value && !refresh) return;
      
    //   try {
    //     isLoadingPublished.value = true;
        
    //     if (refresh) {
    //       lastPublishedId.value = null;
    //       noMorePublished.value = false;
    //       publishedMoments.value = [];
    //     }
        
    //     if (noMorePublished.value && !refresh) return;
        
    //     const params = {
    //       user_id: user.value.id,
    //       limit: publishedPageSize
    //     };
        
    //     if (!refresh && lastPublishedId.value) {
    //       params.last_id = lastPublishedId.value;
    //     }
        
    //     const response = await axios.get(`${API_CONFIG.BASE_URL}/article/user_moments`, {
    //       headers: { Authorization: `Bearer ${store.state.token}` },
    //       params
    //     });
        
    //     const newMoments = response.data.map(moment => ({
    //       ...moment,
    //       showCommentInput: false,
    //       commentInput: '',
    //       showAllComments: false,
    //       isLiked: moment.like_users?.includes(user.value.id) || false,
    //       stats: {
    //         likes: moment.stats.likes || 0,
    //         comments: moment.stats.comments || 0
    //       }
    //     }));
        
    //     if (refresh) {
    //       publishedMoments.value = newMoments;
    //     } else {
    //       publishedMoments.value = [...publishedMoments.value, ...newMoments];
    //     }
        
    //     if (newMoments.length > 0) {
    //       lastPublishedId.value = newMoments[newMoments.length - 1].id;
    //     }
    //     noMorePublished.value = newMoments.length < publishedPageSize;
        
    //   } catch (error) {
    //     console.error('获取发布内容失败:', error);
    //     ElMessage.error('获取发布内容失败');
    //   } finally {
    //     isLoadingPublished.value = false;
    //   }
    // };

    // const fetchLikedMoments = async (refresh = false) => {
    //   if (isLoadingLiked.value && !refresh) return;
      
    //   try {
    //     isLoadingLiked.value = true;
        
    //     if (refresh) {
    //       lastLikedId.value = null;
    //       noMoreLiked.value = false;
    //       likedMoments.value = [];
    //     }
        
    //     if (noMoreLiked.value && !refresh) return;
        
    //     const params = {
    //       user_id: user.value.id,
    //       limit: likedPageSize
    //     };
        
    //     if (!refresh && lastLikedId.value) {
    //       params.last_id = lastLikedId.value;
    //     }
        
    //     const response = await axios.get(`${API_CONFIG.BASE_URL}/article/liked_moments`, {
    //       headers: { Authorization: `Bearer ${store.state.token}` },
    //       params
    //     });
        
    //     const newMoments = response.data.map(moment => ({
    //       ...moment,
    //       showCommentInput: false,
    //       commentInput: '',
    //       showAllComments: false,
    //       isLiked: true,
    //       stats: {
    //         likes: moment.stats?.likes || 0,
    //         comments: moment.stats?.comments || 0
    //       }
    //     }));
        
    //     if (refresh) {
    //       likedMoments.value = newMoments;
    //     } else {
    //       likedMoments.value = [...likedMoments.value, ...newMoments];
    //     }
        
    //     if (newMoments.length > 0) {
    //       lastLikedId.value = newMoments[newMoments.length - 1].id;
    //     }
    //     noMoreLiked.value = newMoments.length < likedPageSize;
        
    //   } catch (error) {
    //     console.error('获取喜欢内容失败:', error);
    //     ElMessage.error('获取喜欢内容失败');
    //   } finally {
    //     isLoadingLiked.value = false;
    //   }
    // };

    const switchTab = (tab) => {
      activeTab.value = tab;
      if (tab === 'published' && publishedMoments.value.length === 0) {
        fetchPublishedMoments();
      } else if (tab === 'liked' && likedMoments.value.length === 0) {
        fetchLikedMoments();
      }
    };

    const logout = () => {
      store.dispatch('logout');
      router.push('/login');
    };

    const goToUserDetail = () => {
      router.push(`/user/userinfo/${user.value.id}`);
    };

    const toggleUserInfo = () => {
      isUserInfoOpen.value = !isUserInfoOpen.value;
    };

    const likeMoment = async (momentId) => {
      const targetArray = activeTab.value === 'published' ? publishedMoments : likedMoments;
      const targetMoment = targetArray.value.find(moment => moment.id === momentId);
      
      if (!targetMoment) return;

      try {
        targetMoment.isLiked = !targetMoment.isLiked;
        targetMoment.stats.likes += targetMoment.isLiked ? 1 : -1;

        const response = await axios.post(`${API_CONFIG.BASE_URL}/article/like_moment`, {
          moment_id: momentId,
          user_id: user.value.id,
          is_like: targetMoment.isLiked
        }, {
          headers: {
            Authorization: `Bearer ${store.state.token}`
          }
        });

        if (response.data.success) {
          targetMoment.isLiked = response.data.is_liked;
          targetMoment.stats.likes = response.data.likes_count;
        }
      } catch (error) {
        targetMoment.isLiked = !targetMoment.isLiked;
        targetMoment.stats.likes -= targetMoment.isLiked ? 1 : -1;
        
        console.error('点赞操作失败:', error);
      }
    };

    const deleteMoment = async (momentId, listType) => {
      if (!confirm('确定要删除这条动态吗？')) return;

      try {
        await axios.post(
          `${API_CONFIG.BASE_URL}/article/delete/moment`,
          { moment_id: momentId },
          { headers: { Authorization: `Bearer ${store.state.token}` } }
        );

        if (listType === 'published') {
          publishedMoments.value = publishedMoments.value.filter(m => m.id !== momentId);
        } else if (listType === 'liked') {
          likedMoments.value = likedMoments.value.filter(m => m.id !== momentId);
        }
        
        ElMessage.success('删除成功');
      } catch (error) {
        console.error('删除失败:', error);
        ElMessage.error('删除失败');
      }
    };

    const handleScroll = () => {
      if (activeTab.value !== 'liked' || isLoadingLiked.value || noMoreLiked.value) return;
      
      const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
      
      if (scrollTop + clientHeight >= scrollHeight - 100) {
        fetchLikedMoments();
      }
    };

    onMounted(() => {
      if (!store.state.user) {
        router.push('/login');
      } else {
        fetchPublishedMoments();
      }
      
      window.addEventListener('scroll', handleScroll);
    });

    onUnmounted(() => {
      window.removeEventListener('scroll', handleScroll);
    });

    return {
      user,
      displayName,
      avatarUrl,
      getVideoTypeContent,
      logout,
      goToUserDetail,
      isUserInfoOpen,
      toggleUserInfo,
      activeTab,
      switchTab,
      publishedMoments,
      likedMoments,
      getFullUrl,
      formatTime,
      getTimeAgo,
      sanitizeHtml,
      openImagePreview,
      closeImagePreview,
      showImagePreview,
      currentPreviewImage,
      defaultAvatar,
      likeMoment,
      goToMomentDetail,
      deleteMoment,
      currentUser
    };
  },
};
</script>
<style scoped>
/* 布局结构 */
.user-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #f8f8f8;
  position: relative;
}

.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  z-index: 100;
  padding: 0 20px;
  display: flex;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  margin-right: 12px;
  border: 2px solid #07c160;
  padding: 2px;
}

.username {
  font-weight: 500;
  font-size: 16px;
  color: #333;
}

.main-layout {
  display: flex;
  flex: 1;
  margin-top: 60px;
}

.main-content {
  flex: 1;
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
  padding: 20px;
}

/* 标签页样式 */
.content-tabs {
  display: flex;
  justify-content: center;
  border-bottom: 1px solid #eaeaea;
  margin-bottom: 20px;
  padding: 0 20px;
}


.tab {
  padding: 12px 40px;
  cursor: pointer;
  font-size: 16px;
  color: #666;
  position: relative;
  margin: 0 10px;
  transition: all 0.3s ease;
}


.tab:hover {
  color: #1890ff;
}


.tab.active {
  color: #1890ff;
  font-weight: 500;
}


.tab.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 20%;
  right: 20%;
  height: 2px;
  background-color: #1890ff;
  transition: all 0.3s ease;
}


/* 动态项样式 */
.moment-item {
  background: #fff;
  margin-bottom: 20px;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

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

.moment-content {
  font-size: 16px;
  line-height: 1.6;
  color: #333;
}

/* 媒体内容 */
.media-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 12px;
}

.media-item {
  height: 120px;
  overflow: hidden;
  border-radius: 4px;
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

/* 视频容器 */
.video-container {
  position: relative;
  height: 100%;
  background: #000;
}

video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 互动区域 */
.moment-interaction {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-top: 10px;
  color: #999;
  font-size: 12px;
  gap: 16px;
}

.like-container, .comment-container {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: color 0.2s;
}

.like-container:hover, .comment-container:hover {
  color: #07c160;
}

.like-container i, .comment-container i {
  color: #999;
}

.liked {
  color: #07c160 !important;
}

.delete-btn {
  color: #999;
  font-size: 16px;
  transition: all 0.2s;
}

.delete-btn:hover {
  color: #f56c6c;
}

/* 底部信息 */
.moment-footer {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  margin-top: 10px;
  color: #999;
  font-size: 12px;
}

.time-ago {
  margin-right: 16px;
}

/* 图片预览 */
.image-preview-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.image-preview-content {
  position: relative;
  max-width: 90%;
  max-height: 90%;
}

.close-preview {
  position: absolute;
  top: -30px;
  right: 0;
  background: none;
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
}

.preview-image {
  max-width: 100%;
  max-height: 85vh;
  object-fit: contain;
  border-radius: 4px;
}

/* 响应式调整 */
@media (max-width: 640px) {
  .main-content {
    padding: 0 15px;
  }
  
  .moment-item {
    padding: 15px;
  }
  
  .tab {
    padding: 12px 20px;
    font-size: 14px;
  }
  
  .media-item {
    height: 100px;
  }
}

/* 加载提示 */
.loading-tip, .no-more-tip {
  text-align: center;
  padding: 15px 0;
  color: #999;
  font-size: 14px;
}

.loading-tip i {
  margin-right: 5px;
}
</style>