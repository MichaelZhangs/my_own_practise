<template>
  <div class="user-page">
    <header class="header">
      <div class="header-left">
        <div class="user-info" @click="goToUserDetail">
          <img :src="avatarUrl" alt="用户头像" class="avatar" />
          <span class="username">{{ displayName }}</span>
        </div>
      </div>
      
      <div class="header-right">
        <div class="relative">
          <button class="add-group-button" @click.stop="openCreateGroupDialog">
            <i class="fa fa-plus" aria-hidden="true"></i>
          </button>
        </div>

        <button @click="logout" class="logout-button">退出登录</button>
      </div>
    </header>

    <div class="main-layout">
      <aside class="sidebar">
        <div class="sidebar-search">
          <div class="search-toggle" @click="toggleSearch">
            <i class="fa fa-search" aria-hidden="true"></i>
            <span>搜索用户</span>
          </div>
          
          <div v-if="isSearchOpen" class="search-box">
            <div class="search-input-group">
              <input 
                type="text" 
                v-model="searchKeyword" 
                placeholder="搜索用户..." 
                @keyup.enter="searchUsers"
              />
              <button class="search-button" @click="searchUsers">
                <i class="fa fa-search" aria-hidden="true"></i>
              </button>
              <button class="cancel-button" @click="toggleSearch">
                取消
              </button>
            </div>
            
            <div v-if="isSearching" class="search-loading">
              <i class="fa fa-spinner fa-spin" aria-hidden="true"></i> 搜索中...
            </div>
            
            <div v-else-if="searchResults.length > 0" class="search-results">
              <div 
                v-for="user in searchResults" 
                :key="user.id" 
                class="search-result-item"
                @click="startChat(user)"
              >
                <div class="result-avatar-container">
                  <img 
                    :src="getFullUrl(user.photo)|| defaultAvatar" 
                    alt="用户头像" 
                    class="result-avatar"
                  />
                </div>
                <div class="result-info">
                  <div class="result-name">{{ user.username }}</div>
                  <div class="result-phone">{{ user.phone }}</div>
                </div>
              </div>
            </div>
            
            <div v-else-if="searchKeyword && !isSearching" class="no-results">
              没有找到匹配的用户
            </div>
          </div>
        </div>

        <ul class="menu">
          <li class="menu-item">
            <router-link to="/user/dashboard" class="menu-link">仪表盘</router-link>
          </li>
          <li class="menu-item">
            <router-link to="/user-moment" class="menu-link">我相关</router-link>
          </li>
          <li class="menu-item">
            <router-link to="/moments" class="menu-link">朋友圈</router-link>
          </li>
          <li class="menu-item">
            <div @click="toggleUserInfo" class="menu-title">
              用户信息
              <span class="arrow">{{ isUserInfoOpen ? '▼' : '▶' }}</span>
            </div>
            <ul v-if="isUserInfoOpen" class="sub-menu">
              <li class="sub-menu-item">
                <router-link to="/user/userinfo/userlist" class="sub-menu-link">用户列表</router-link>
              </li>
              <li class="sub-menu-item">
                <router-link to="/user/bigdatauser" class="sub-menu-link">大数据用户</router-link>
              </li>
            </ul>
          </li>
        </ul>

        <!-- 加入的群模块 -->
        <div class="joined-groups">
          <div 
            class="joined-groups-title" 
            @click="toggleJoinedGroupsCollapse"
          >
            加入的群
            <span>{{ isJoinedGroupsCollapse ? '▶' : '▼' }}</span>
          </div>
          <div 
            class="joined-group-list" 
            v-show="!isJoinedGroupsCollapse"
          >
            <div
              v-for="group in joinedGroups"
              :key="group.id"
              class="joined-group-item"
              @click="startChat(group)"
            >
              <div class="result-avatar-container" >
                <div class="group-avatar">
                  <div 
                    v-for="(avatarUrl, idx) in getGroupAvatarUrls(group)" 
                    :key="idx"
                    class="group-avatar-member"
                    :style="getAvatarPosition(idx)"
                  >
                    <img 
                      :src="avatarUrl" 
                      alt="成员头像"
                    />
                  </div>
                </div>
              </div>
              <div class="result-info">
                <div class="result-name">{{ group.username }}</div>
                <div class="group-members-count">
                  {{ group.members?.length || 0 }}人
                </div>
                <div v-if="group.lastMessage" class="last-message">
                  {{ group.lastMessage }}
                </div>
              </div>
              <div v-if="group.unreadCount > 0" class="unread-count">
                {{ group.unreadCount > 99 ? '99+' : group.unreadCount }}
              </div>
            </div>
          </div>
        </div>

        <div class="recent-chats">
          <div 
            class="recent-chats-title" 
            @click="toggleRecentChatCollapse"
          >
            最近聊天
            <span>{{ isRecentChatCollapse ? '▶' : '▼' }}</span>
          </div>
          <div 
            class="recent-chat-list" 
            v-show="!isRecentChatCollapse"
          >
            <div
              v-for="(chat, index) in recentChats"
              :key="index"
              class="recent-chat-item"
              @click="startChat(chat)"
            >
              <div class="result-avatar-container">
                <div v-if="chat.isGroup" class="group-avatar">
                  <div 
                    v-for="(avatarUrl, idx) in getGroupAvatarUrls(chat)" 
                    :key="idx"
                    class="group-avatar-member"
                    :style="getAvatarPosition(idx)"
                  >
                    <img 
                      :src="avatarUrl" 
                      alt="成员头像"
                    />
                  </div>
                </div>
                <img
                  v-else
                  :src="getFullUrl(chat.photo) || defaultAvatar"
                  alt="用户头像"
                  class="result-avatar"
                />
              </div>
              <div class="result-info">
                <div class="result-name">{{ chat.username }}</div>
                <div v-if="chat.isGroup" class="group-members-count">
                  {{ chat.group_members?.length || 0 }}人
                </div>
                <div v-if="chat.lastMessage" class="last-message">
                  {{ chat.lastMessage }}
                </div>
              </div>
              <div v-if="chat.unreadCount > 0" class="unread-count">
                {{ chat.unreadCount > 99 ? '99+' : chat.unreadCount }}
              </div>
            </div>
          </div>
        </div>
      </aside>

      <main class="main-content">
        <router-view />
      </main>
    </div>
    
    <div 
      class="group-dialog-mask" 
      v-if="showCreateGroupDialog"
      v-click-outside="() => showCreateGroupDialog = false"
    >
      <div class="group-dialog">
        <div class="dialog-header">
          <h3>创建群聊</h3>
          <button class="close-button" @click="showCreateGroupDialog = false">
            <i class="fa fa-times" aria-hidden="true"></i>
          </button>
        </div>
        
        <div class="dialog-body">
          <div class="search-box">
            <input 
              type="text" 
              v-model="groupSearchKeyword" 
              placeholder="搜索用户..." 
              @input="filterGroupUsers"
            />
          </div>
          
          <div class="selected-users" v-if="selectedUsers?.length > 0">
            <div class="selected-title">已选 {{ selectedUsers?.length }} 人</div>
            <div class="selected-avatars">
              <div 
                v-for="user in selectedUsers" 
                :key="user.id"
                class="selected-avatar"
                @click="removeUser(user.id)"
              >
                <img :src="getFullUrl(user.photo) || defaultAvatar" alt="用户头像" />
                <span class="remove-icon">×</span>
              </div>
            </div>
          </div>
          
          <div class="group-name-input">
            <input 
              type="text" 
              v-model="groupName" 
              placeholder="请输入群聊名称"
            />
          </div>
          
          <div class="user-list">
            <div class="list-header">选择联系人</div>
            <div 
              v-for="user in filteredUsers" 
              :key="user.id"
              class="user-item"
              @click="toggleUserSelection(user)"
              :class="{ selected: isUserSelected(user.id) }"
            >
              <div class="result-avatar-container">
                <img 
                  :src="getFullUrl(user.photo) || defaultAvatar" 
                  alt="用户头像" 
                  class="result-avatar"
                />
              </div>
              <div class="result-info">
                <div class="result-name">{{ user.username }}</div>
                <div class="result-phone">{{ user.phone }}</div>
              </div>
              <div class="selection-indicator" v-if="isUserSelected(user.id)">
                <i class="fa fa-check" aria-hidden="true"></i>
              </div>
            </div>
            <div 
              v-if="pagination.hasMore && !pagination.loading" 
              class="load-more-trigger"
              ref="loadMoreTrigger"
            ></div>
            <div v-if="pagination.loading" class="loading-more">
              <i class="fa fa-spinner fa-spin"></i> 加载中...
            </div>
            <div v-if="!pagination.hasMore && allUsers?.length > 0" class="no-more-data">
              没有更多数据了
            </div>
          </div>
        </div>
        
        <div class="dialog-footer">
          <button 
            class="cancel-btn" 
            @click="showCreateGroupDialog = false"
          >
            取消
          </button>
          <button 
            class="create-btn" 
            @click="createGroup"
            :disabled="selectedUsers.length < 2"
          >
            创建
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref, onMounted, watch } from 'vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';
import defaultAvatar from '@/assets/default-avatar.png';
import { API_CONFIG } from '@/config/config';
import axios from 'axios';
import { ElMessage } from 'element-plus';
import { debounce } from 'lodash';
import { useIntersectionObserver } from '@vueuse/core';
import { extractAndNormalizeId } from '@/store/modules/chat'; // 导入辅助函数

export default {
  setup() {
    const store = useStore();
    const router = useRouter();
    
    // 状态管理
    const isUserInfoOpen = ref(false);
    const isSearchOpen = ref(false);
    const searchKeyword = ref('');
    const searchResults = ref([]);
    const isSearching = ref(false);
    const isRecentChatCollapse = ref(false);
    const isJoinedGroupsCollapse = ref(false);
    const showCreateGroupDialog = ref(false);
    const groupSearchKeyword = ref('');
    const groupName = ref('');
    const selectedUsers = ref([]);
    const allUsers = ref([]);
    
    const socket = ref(null); // WebSocket 实例
    const messages = ref([]); // 聊天消息
    const inputMessage = ref(''); // 输入框内容

    // 分页控制
    const pagination = ref({
      page: 1,
      pageSize: 10,
      total: 0,
      loading: false,
      hasMore: true
    });
    
    const loadMoreTrigger = ref(null);
    
    // 计算属性
    const user = computed(() => store.state.user);
    const displayName = computed(() => user.value?.username || '未登录');
    
    const recentChats = computed(() => {
  const chats = store.getters['chat/getRecentChats'] || [];
  return chats.map(chat => ({
    ...chat,
    avatarMembers: chat.avatar_members || [] // 确保有avatarMembers字段
  }));
});

  const joinedGroups = computed(() => {
    const groups = store.getters['chat/getJoinedGroups'] || [];
    console.log("当前joinedGroups:", groups);
    return groups.map(group => ({
      ...group,
      username: group.name || group.username || '未命名群聊', // 确保使用正确的名称
      avatarMembers: group.avatar_members || []
    }));
  });


    const isUserLoggedIn = computed(() => !!user.value?.id);
    
    const avatarUrl = computed(() => {
      if (user.value?.photo) {
        return `${API_CONFIG.BASE_URL}${user.value.photo}`;
      }
      return defaultAvatar;
    });
    
    // 方法定义
    const getFullUrl = (path) => {
      if (!path || path === defaultAvatar) return path;
      return path.startsWith('http') ? path : `${API_CONFIG.BASE_URL}${path}`;
    };

    const getGroupAvatar = async (groupId) => {
  try {
    const avatarMembers = await store.dispatch('chat/fetchGroupAvatar', groupId);
    console.log("avatars: ", avatarMembers)
    return avatarMembers || [];
  } catch (error) {
    console.error('获取群头像失败:', error);
    return [];
  }
};

const showGroupInfo = (group) => {
  if (!group?.id) {
    ElMessage.warning('无法获取群信息');
    return;
  }
  
  router.push({
    name: 'GroupInfo',
    params: { id: group.id }
  });
};

const getGroupAvatarUrls = (chat) => {
  if (!chat) return []; // 防御性检查
  // 优先使用 avatarMembers
  if (chat.avatarMembers && chat.avatarMembers.length > 0) {
    return chat.avatarMembers.map(url => getFullUrl(url)).filter(Boolean);
  }
  
  // 如果没有 avatarMembers，使用成员ID获取头像
  const members = chat.group_members || chat.members || [];
  return getFirstMembers(members, 9).map(memberId => getMemberAvatar(memberId));
};
// 修改getMemberAvatar方法
const getMemberAvatar = (memberId) => {
  // 先检查是否是当前用户
  if (memberId === user.value?.id) {
    return avatarUrl.value;
  }
  
  // 检查 allUsers 中是否有该成员
  const member = allUsers.value?.find(u => u?.id === memberId);
  
  // 如果有成员信息且包含头像，则返回头像URL
  if (member?.photo) {
    return getFullUrl(member.photo);
  }
  
  // 否则返回默认头像
  return defaultAvatar;
};

    
    const getFirstMembers = (members, count) => {
      if (!members) return [];
      return members.slice(0, count);
    };
    
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
    
    const loadAllUsers = async () => {
      try {
        if (!pagination.value.hasMore || pagination.value.loading) {
          return;
        }

        pagination.value.loading = true;
        
        const response = await axios.get(`${API_CONFIG.BASE_URL}/user/get-users`, {
          params: {
            page: pagination.value.page,
            page_size: pagination.value.pageSize
          },
          headers: { Authorization: `Bearer ${store.state.token}` }
        }).catch(error => {
          throw new Error(`请求失败: ${error.message}`);
        });
        
        const userList = (() => {
          try {
            const data = response?.data ?? {};
            if (Array.isArray(data)) return data;
            if (Array.isArray(data.data)) return data.data;
            if (Array.isArray(data.users)) return data.users;
            if (Array.isArray(data.list)) return data.list;
            if (Array.isArray(data.items)) return data.items;
            return [];
          } catch (e) {
            console.error('数据解析错误:', e);
            return [];
          }
        })();
        
        const total = (() => {
          try {
            const data = response?.data ?? {};
            return data.pagination?.total ?? 
                   data.total ?? 
                   data.total_count ?? 
                   data.totalItems ??
                   (userList.length > 0 ? Infinity : 0);
          } catch (e) {
            console.error('总数解析错误:', e);
            return userList.length > 0 ? Infinity : 0;
          }
        })();
        
        allUsers.value = pagination.value.page === 1 
          ? [...userList]
          : [...allUsers.value, ...userList];
        
        pagination.value.total = total;
        
        const receivedCount = userList.length;
        const isLastPage = receivedCount === 0 || 
                          (total !== Infinity && 
                           pagination.value.page * pagination.value.pageSize >= total);
        
        pagination.value.hasMore = !isLastPage;
        
        if (receivedCount === 0 && total === Infinity) {
          pagination.value.hasMore = false;
          console.warn('没有获取到数据，已自动停止加载更多');
        }
        
      } catch (error) {
        console.error('加载用户列表失败:', error);
        ElMessage.error(error.message);
        pagination.value.hasMore = false;
        
        if (pagination.value.page === 1) {
          allUsers.value = [];
        }
      } finally {
        pagination.value.loading = false;
      }
    };
    
    const openCreateGroupDialog = async () => {
      showCreateGroupDialog.value = true;
      groupName.value = '';
      selectedUsers.value = [];
      groupSearchKeyword.value = '';
      pagination.value.page = 1;
      pagination.value.hasMore = true;
      await loadAllUsers();
    };
    
    const filteredUsers = computed(() => {
      if (!groupSearchKeyword.value.trim()) {
        return allUsers.value;
      }
      
      const keyword = groupSearchKeyword.value.toLowerCase().trim();
      return allUsers.value.filter(u => 
        u.username.toLowerCase().includes(keyword) || 
        (u.phone && u.phone.includes(keyword))
      );
    });
    
    const toggleUserSelection = (user) => {
      const index = selectedUsers.value.findIndex(u => u.id === user.id);
      if (index === -1) {
        selectedUsers.value.push(user);
      } else {
        selectedUsers.value.splice(index, 1);
      }
    };
    
    const isUserSelected = (userId) => {
      return selectedUsers.value.some(u => u.id === userId);
    };
    
    const removeUser = (userId) => {
      selectedUsers.value = selectedUsers.value.filter(u => u.id !== userId);
    };
    
const createGroup = async () => {
  if (selectedUsers.value.length < 2) {
    ElMessage.warning('至少选择2位成员');
    return;
  }

  try {
    const groupMembers = selectedUsers.value.map(u => u.id);
    groupMembers.push(user.value.id); // 包含当前用户

    const groupData = {
      name: groupName.value || `群聊 (${selectedUsers.value.length + 1}人)`,
      user_id: user.value.id,
      members: groupMembers
    };

    const response = await axios.post(
      `${API_CONFIG.BASE_URL}/group/create`,
      groupData,
      { headers: { Authorization: `Bearer ${store.state.token}` } }
    );

    if (response.data.msg) {
      ElMessage.success('群聊创建成功');

      // 确保从后端获取最新的 members_count 和 members
      const membersCount = response.data.data?.members_count || groupMembers.length;
      const members = response.data.data?.members || groupMembers;
      console.log("群成员: ",membersCount)


      const groupInfo = {
        id: response.data.data.group_id,
        username: groupData.name,
        photo: response.data.data.photo || null,
        isGroup: true,
        members: members,
        members_count: membersCount, // 关键字段
        lastMessage: '',
        lastMessageTime: new Date().toISOString()
      };

      // 更新 Vuex
      store.commit('chat/ADD_RECENT_CHAT', groupInfo);
      await store.dispatch('chat/saveRecentChat', groupInfo);

      // 强制刷新群聊数据
      await store.dispatch('chat/loadJoinedGroups');
      await store.dispatch('chat/loadRecentChats');
      console.log("群信息: ",response.data.data )
      showCreateGroupDialog.value = false;
      router.push({
        name: 'GroupChat',
        params: { id: response.data.data.group_id },
      });
    }
  } catch (error) {
    console.error('创建群聊失败:', error);
    ElMessage.error('群聊创建失败，请重试');
  }
};
    
const logout = async () => {
  try {
    // 1. 关闭所有活跃的 WebSocket 连接
    if (socket.value) {
      socket.value.close();
      socket.value = null;
    }

    // 2. 调用 Vuex 的 logout action (会清除 token 和用户数据)
    await store.dispatch('logout');

    // 3. 重置所有本地敏感状态
    searchKeyword.value = '';
    searchResults.value = [];
    inputMessage.value = '';
    messages.value = [];
    selectedUsers.value = [];
    allUsers.value = [];

    // 4. 跳转到登录页
    router.push('/login');
  } catch (error) {
    console.error('退出登录失败:', error);
    ElMessage.error('退出登录失败，请重试');
    // 即使失败也强制跳转
    router.push('/login');
  }
};
    
    const goToUserDetail = () => {
      router.push('/user/userinfo/' + user.value?.id);
    };
    
    const toggleUserInfo = () => {
      isUserInfoOpen.value = !isUserInfoOpen.value;
    };
    
    const toggleSearch = () => {
      isSearchOpen.value = !isSearchOpen.value;
      if (!isSearchOpen.value) {
        searchKeyword.value = '';
        searchResults.value = [];
      }
    };
    
    const searchUsers = async () => {
      if (!searchKeyword.value.trim()) {
        searchResults.value = [];
        return;
      }
      
      isSearching.value = true;
      
      try {
        const response = await axios.get(`${API_CONFIG.BASE_URL}/user/search`, {
          params: {
            keyword: searchKeyword.value.trim()
          },
          headers: { Authorization: `Bearer ${store.state.token}` }
        });
        
        searchResults.value = response.data.data || [];
      } catch (error) {
        console.error('搜索用户失败:', error);
        ElMessage.error('搜索用户失败');
      } finally {
        isSearching.value = false;
      }
    };
    
    const debouncedSearchUsers = debounce(searchUsers, 300);
    
    const clearSearch = () => {
      searchKeyword.value = '';
      searchResults.value = [];
    };
    
    const loadRecentChats = async () => {
      try {
        await store.dispatch('chat/loadRecentChats');
        await store.dispatch('chat/loadJoinedGroups');
      } catch (error) {
        console.error('加载聊天数据失败:', error);
      }
    };
    
    // 在setup()中
const getGroupAvatarMembers = async (groupId) => {
  try {
    const avatarMembers = await store.dispatch('chat/fetchGroupAvatar', groupId);
    return avatarMembers || [];
  } catch (error) {
    console.error('获取群头像成员失败:', error);
    return [];
  }
};


const startChat = async (chat) => {
  // 确保使用规范化后的ID
  const normalizedId = chat.id || chat.normalizedId;
  if (!normalizedId) {
    console.error('无法获取有效的聊天ID:', chat);
    ElMessage.error('聊天ID无效');
    return;
  }
  
  const newChat = { ...chat };
  newChat.id = normalizedId;
  newChat.normalizedId = normalizedId; // 确保对象中有normalizedId字段
  
  console.log("开始聊天信息——规范化ID:", normalizedId);
  
  // 对于群聊，确保有members信息
  if (chat.isGroup) {
    // 获取群成员头像URL列表
    newChat.avatarMembers = await getGroupAvatarMembers(normalizedId);
    console.log("newChat 时群信息", newChat);
    
    // 从已加入群聊中获取完整信息
    const joinedGroup = store.getters['chat/getJoinedGroupById'](normalizedId);
    
     const isUserInGroup = joinedGroups.value.some(group => 
      extractAndNormalizeId(group) === normalizedId
    );
    
    if (!isUserInGroup) {
      ElMessage.warning('您已退出该群组，无法进入聊天');
      return;
    }



    if (joinedGroup) {
      newChat.members = joinedGroup.members || [];
      newChat.membersCount = joinedGroup.membersCount || 0;
      console.log("从Vuex获取的群聊信息:", joinedGroup);
    } else {
      console.warn(`未找到群聊信息，ID: ${normalizedId}，尝试刷新群聊信息`);
      await store.dispatch('chat/refreshJoinedGroup', normalizedId);
      const refreshedGroup = store.getters['chat/getJoinedGroupById'](normalizedId);
      if (refreshedGroup) {
        newChat.members = refreshedGroup.members || [];
        newChat.membersCount = refreshedGroup.membersCount || 0;
        console.log("刷新后获取的群聊信息:", refreshedGroup);
      }
    }
  }
  
  // 保存到最近聊天
  store.commit('chat/ADD_RECENT_CHAT', newChat);
  await store.dispatch('chat/saveRecentChat', newChat);
  
  // 清除未读计数
  await store.dispatch('chat/clearUnreadCount', normalizedId);
  
    // 设置当前聊天ID
  store.commit('chat/SET_CURRENT_CHAT_ID', normalizedId);


  // 如果是搜索状态，重置搜索
  if (isSearchOpen.value) {
    isSearchOpen.value = false;
    searchKeyword.value = '';
    searchResults.value = [];
  }
  
  console.log("点击聊天后路由跳转，ID:",chat.isGroup, normalizedId, normalizedId);
  
  router.push({
    name: chat.isGroup ? 'GroupChat' : 'Chat',
    params: { id: normalizedId },
  });
};
    
    const toggleRecentChatCollapse = () => {
      isRecentChatCollapse.value = !isRecentChatCollapse.value;
    };
    
    const toggleJoinedGroupsCollapse = () => {
      isJoinedGroupsCollapse.value = !isJoinedGroupsCollapse.value;
    };
    
    // 生命周期钩子
    onMounted(() => {
      useIntersectionObserver(
        loadMoreTrigger,
        ([{ isIntersecting }]) => {
          if (isIntersecting && 
              !pagination.value.loading && 
              pagination.value.hasMore) {
            pagination.value.page += 1;
            loadAllUsers();
          }
        },
        { threshold: 0.1 }
      );
      
      if (isUserLoggedIn.value) {
        loadRecentChats();
      }
    });
    
    watch(searchKeyword, (newVal) => {
      if (newVal.trim()) {
        debouncedSearchUsers();
      } else {
        searchResults.value = [];
      }
    });
    
    watch(user, (newUser) => {
      if (newUser?.id) {
        loadRecentChats();
      }
    });

    watch(() => store.state.chat.joinedGroups, (newGroups) => {
      console.log("群组列表已更新:", newGroups);
    }, { deep: true });

// 或者添加一个刷新群组的方法
const refreshJoinedGroups = async () => {
  await store.dispatch('chat/loadJoinedGroups');
};
    
    return {
      user,
      displayName,
      avatarUrl,
      getFullUrl,
      logout,
      refreshJoinedGroups,
      goToUserDetail,
      isUserInfoOpen,
      toggleUserInfo,
      isSearchOpen,
      getGroupAvatar,
      getGroupAvatarUrls,
      searchKeyword,
      searchResults,
      isSearching,
      toggleSearch,
      clearSearch,
      startChat,
      defaultAvatar,
      recentChats,
      joinedGroups,
      isRecentChatCollapse,
      toggleRecentChatCollapse,
      isJoinedGroupsCollapse,
      toggleJoinedGroupsCollapse,
      showCreateGroupDialog,
      groupSearchKeyword,
      groupName,
      selectedUsers,
      filteredUsers,
      openCreateGroupDialog,
      toggleUserSelection,
      isUserSelected,
      removeUser,
      createGroup,
      getMemberAvatar,
      getFirstMembers,
      getAvatarPosition,
      showGroupInfo,
      pagination,
      loadMoreTrigger
    };
  },
  
  directives: {
    'click-outside': {
      mounted(el, binding) {
        el.clickOutsideEvent = function(event) {
          if (!(el === event.target || el.contains(event.target))) {
            binding.value(event);
          }
        };
        document.addEventListener('click', el.clickOutsideEvent);
      },
      unmounted(el) {
        document.removeEventListener('click', el.clickOutsideEvent);
      }
    }
  }
};
</script>

<style scoped>
.user-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #f0f2f5;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 60px;
  background-color: #001529;
  color: white;
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
  margin-right: 10px;
}

.username {
  margin-right: 20px;
  font-size: 16px;
}

.logout-button {
  padding: 5px 10px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.logout-button:hover {
  background-color: #40a9ff;
}

.main-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 200px;
  background-color: #001529;
  color: white;
  overflow-y: auto;
}

.menu {
  list-style: none;
  padding: 0;
  margin: 0;
}

.menu-item {
  padding: 15px 20px;
  border-bottom: 1px solid #002140;
}

.menu-link {
  color: white;
  text-decoration: none;
  font-size: 14px;
}

.menu-link:hover {
  color: #1890ff;
}

.menu-title {
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.arrow {
  font-size: 12px;
}

.sub-menu {
  list-style: none;
  padding: 0;
  margin: 10px 0 0 20px;
}

.sub-menu-item {
  padding: 10px 0;
}

.sub-menu-link {
  color: white;
  text-decoration: none;
  font-size: 14px;
}

.sub-menu-link:hover {
  color: #1890ff;
}

.main-content {
  flex: 1;
  padding: 20px;
  background-color: white;
  overflow-y: auto;
  position: relative;
}

.sidebar-search {
  padding: 15px 20px;
  border-bottom: 1px solid #002140;
}

.search-toggle {
  cursor: pointer;
  display: flex;
  align-items: center;
  font-size: 14px;
}

.search-toggle i {
  margin-right: 10px;
}

.search-box {
  margin-top: 10px;
  background-color: #002140;
  border-radius: 4px;
  padding: 10px;
}

.search-input-group {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.search-input-group input {
  flex: 1;
  padding: 8px;
  border: 1px solid #003a75;
  border-radius: 4px 0 0 4px;
  outline: none;
  background-color: #003a75;
  color: white;
}

.search-input-group input::placeholder {
  color: #8c8c8c;
}

.search-button, .cancel-button {
  padding: 8px 12px;
  background-color: #1890ff;
  color: white;
  border: none;
  cursor: pointer;
}

.search-button {
  border-radius: 0 4px 4px 0;
}

.cancel-button {
  margin-left: 5px;
  border-radius: 4px;
  background-color: #f5222d;
}

.search-loading, .no-results {
  padding: 10px;
  text-align: center;
  color: #8c8c8c;
}

.search-results {
  max-height: 300px;
  overflow-y: auto;
}

.search-result-item {
  display: flex;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid #003a75;
  cursor: pointer;
}

.search-result-item:hover {
  background-color: #003a75;
}

.result-avatar-container {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  overflow: hidden;
  margin-right: 10px;
  position: relative;
}

.result-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.group-avatar {
  position: relative;
  width: 32px;
  height: 32px;
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

.result-info {
  flex: 1;
  min-width: 0;
}

.result-name {
  font-weight: bold;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-phone {
  font-size: 12px;
  color: #8c8c8c;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.group-members-count {
  font-size: 12px;
  color: #8c8c8c;
  margin-top: 2px;
}

.last-message {
  font-size: 12px;
  color: #8c8c8c;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-chats {
  padding: 15px 20px;
  border-bottom: 1px solid #002140;
}

.recent-chats-title {
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 10px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
}

.recent-chat-list {
  max-height: 300px;
  overflow-y: auto;
}

.recent-chat-item {
  display: flex;
  align-items: center;
  padding: 10px 0;
  cursor: pointer;
  position: relative;
}

.recent-chat-item:hover {
  background-color: #003a75;
}

.unread-count {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background-color: #f5222d;
  color: white;
  border-radius: 50%;
  min-width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  padding: 0 4px;
}

.add-group-button {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.1);
  color: white;
  border: none;
  margin-right: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-group-button:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.group-dialog-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.group-dialog {
  background-color: white;
  border-radius: 4px;
  width: 400px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.dialog-header {
  padding: 15px 20px;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

.dialog-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

.close-button {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  color: #999;
}

.close-button:hover {
  color: #333;
}

.dialog-body {
  flex: 1;
  overflow-y: auto;
  padding: 15px 20px;
}

.dialog-body .search-box {
  margin-bottom: 15px;
}

.dialog-body .search-box input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  outline: none;
}

.dialog-body .search-box input:focus {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.selected-users {
  margin-bottom: 15px;
}

.selected-title {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.selected-avatars {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.selected-avatar {
  position: relative;
  cursor: pointer;
}

.selected-avatar img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

.remove-icon {
  position: absolute;
  top: -4px;
  right: -4px;
  background-color: #f5222d;
  color: white;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
}

.group-name-input {
  margin-bottom: 15px;
}

.group-name-input input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  outline: none;
}

.group-name-input input:focus {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.user-list {
  max-height: 300px;
  overflow-y: auto;
}

.list-header {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 10px;
  color: #333;
}

.user-item {
  display: flex;
  align-items: center;
  padding: 10px 0;
  cursor: pointer;
  border-bottom: 1px solid #e8e8e8;
  position: relative;
}

.user-item:last-child {
  border-bottom: none;
}

.user-item:hover {
  background-color: #f5f5f5;
}

.user-item.selected {
  background-color: #e6f7ff;
}

.selection-indicator {
  color: #1890ff;
  font-size: 16px;
  position: absolute;
  right: 10px;
}

.dialog-footer {
  padding: 15px 20px;
  border-top: 1px solid #e8e8e8;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.cancel-btn, .create-btn {
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid #d9d9d9;
  background-color: white;
  color: #333;
}

.create-btn {
  background-color: #1890ff;
  color: white;
  border-color: #1890ff;
}

.create-btn:disabled {
  background-color: #f5f5f5;
  color: rgba(0, 0, 0, 0.25);
  border-color: #d9d9d9;
  cursor: not-allowed;
}

.load-more-trigger {
  height: 1px;
  width: 100%;
}

.loading-more {
  text-align: center;
  padding: 10px;
  color: #999;
  font-size: 14px;
}

.loading-more i {
  margin-right: 5px;
}

.no-more-data {
  text-align: center;
  padding: 10px;
  color: #999;
  font-size: 14px;
}

/* 加入的群相关样式 */
.joined-groups {
  padding: 15px 20px;
  border-bottom: 1px solid #002140;
}

.joined-groups-title {
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 10px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
}

.joined-group-list {
  max-height: 300px;
  overflow-y: auto;
}

.joined-group-item {
  display: flex;
  align-items: center;
  padding: 10px 0;
  cursor: pointer;
  position: relative;
}

.joined-group-item:hover {
  background-color: #003a75;
}
</style>