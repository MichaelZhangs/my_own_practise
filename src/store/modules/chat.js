import axios from 'axios';
import { API_CONFIG } from '@/config/config';
import { ElMessage } from 'element-plus';

// 辅助函数：规范化ID - 区分群聊和单聊
function normalizeId(id, isGroup = false) {
  if (typeof id === 'undefined' || id === null) {
    console.error('normalizeId 错误：ID为undefined或null');
    return null;
  }
  
  // 群聊ID处理
  if (isGroup) {
    // 如果是数字，转为字符串并添加group_前缀
    if (typeof id === 'number') {
      return `group_${id}`;
    }
    
    // 如果是字符串但不是以group_开头，添加前缀
    if (typeof id === 'string' && !id.startsWith('group_')) {
      return `group_${id}`;
    }
    
    // 其他情况保持原样
    return String(id);
  }
  
  // 单聊ID处理 - 确保为数字类型
  if (typeof id === 'number') {
    return id;
  }
  
  // 尝试将字符串转为数字
  const numericId = Number(id);
  if (!isNaN(numericId)) {
    return numericId;
  }
  
  // 如果无法转为数字，保持字符串（但这种情况应该不会发生在单聊中）
  console.warn(`单聊ID无法转换为数字，使用原始值: ${id}`);
  return id;
}

// 辅助函数：从对象中提取并规范化ID
function extractAndNormalizeId(obj) {
  if (!obj) return null;
  
  // 优先使用normalizedId
  if (obj.normalizedId) {
    return obj.normalizedId;
  }
  
  // 尝试从多个可能的字段获取ID
  const id = obj.id || obj.group_id || obj.target_id;
  
  // 判断是否是群聊
  const isGroup = obj.isGroup === true || obj.is_group === true || 
                 (typeof id === 'string' && id.startsWith('group_'));
  
  return normalizeId(id, isGroup);
}

export const chatModule = {
  namespaced: true,
  state: {
    recentChats: [],    // 所有最近聊天（按时间排序）- 只包含单聊
    recentUsers: [],    // 最近单聊
    joinedGroups: [],   // 已加入的群聊列表
    currentChatId: null // 当前选中的聊天ID
  },
  mutations: {
    // 设置当前聊天ID
    SET_CURRENT_CHAT_ID(state, chatId) {
      state.currentChatId = chatId;
    },
    
    // 添加或更新最近聊天（只处理单聊）
    ADD_RECENT_CHAT(state, chat) {
      const isGroup = chat.isGroup === true;
      
      // 如果是群聊，直接返回，不添加到最近聊天
      if (isGroup) {
        return;
      }
      
      const chatId = (chat.user_id || chat.id)?.toString();
      
      if (!chatId) return;

      const existingIndex = state.recentUsers.findIndex(item => item.id.toString() === chatId);

      // 更新或添加记录
      if (existingIndex !== -1) {
        state.recentUsers[existingIndex] = {
          ...state.recentUsers[existingIndex],
          ...chat,
          id: chatId
        };
      } else {
        state.recentUsers.unshift({ ...chat, id: chatId });
      }

      updateCombinedChats(state);
    },
    
    // 初始化最近聊天（只包含单聊）
    INIT_RECENT_CHATS(state, chats) {
      const normalizedChats = chats.map(chat => {
        const normalizedId = extractAndNormalizeId(chat);
        return {
          ...chat,
          id: normalizedId,
          normalizedId // 添加规范化后的ID
        };
      });
      
      // 只保留单聊
      const users = normalizedChats.filter(chat => chat.isGroup !== true);
      
      state.recentUsers = users;
      
      updateCombinedChats(state);
    },
    
    // 初始化已加入的群聊
    INIT_JOINED_GROUPS(state, groups) {
      state.joinedGroups = (groups || []).map(group => {
        const normalizedId = extractAndNormalizeId(group);
        
        return {
          ...group,
          id: normalizedId,
          normalizedId, // 添加规范化后的ID
          target_id: normalizedId,
          isGroup: true,
          members: Array.isArray(group.members) ? [...new Set(group.members)] : [],
          membersCount: group.membersCount
        };
      });
      
      console.log("处理后的群组数据:", state.joinedGroups);
    },
    
    // 更新单个群聊信息（不自动添加到最近聊天）
    UPDATE_JOINED_GROUP(state, updatedGroup) {
      const normalizedId = extractAndNormalizeId(updatedGroup);
      const index = state.joinedGroups.findIndex(g => extractAndNormalizeId(g) === normalizedId);
      
      if (index !== -1) {
        // 更新现有群组信息
        state.joinedGroups.splice(index, 1, { 
          ...state.joinedGroups[index], 
          ...updatedGroup,
          username: updatedGroup.name || updatedGroup.username, // 确保username也更新
          name: updatedGroup.name, // 更新name字段
          id: normalizedId,
          normalizedId
        });
      } else {
        // 如果找不到，添加新群组
        state.joinedGroups.push({ 
          ...updatedGroup, 
          id: normalizedId, 
          isGroup: true,
          normalizedId,
          username: updatedGroup.name || '未命名群聊' // 确保有username
        });
      }
      
      console.log("更新后的群组列表:", state.joinedGroups);
    },
    
    // 从已加入群组中移除群组
    REMOVE_JOINED_GROUP(state, groupId) {
      const normalizedId = extractAndNormalizeId({ id: groupId, isGroup: true });
      state.joinedGroups = state.joinedGroups.filter(group => 
        extractAndNormalizeId(group) !== normalizedId
      );
      
      console.log("移除群组后的列表:", state.joinedGroups);
      
      // 如果当前选中的聊天是这个群组，清除当前选中状态
      if (state.currentChatId === normalizedId) {
        state.currentChatId = null;
      }
    },
    
    // 更新未读计数（只处理单聊）
    UPDATE_UNREAD_COUNT(state, { targetId, count }) {
      // 先判断是否为群聊ID（字符串且以group_开头）
      const isGroup = typeof targetId === 'string' && targetId.startsWith('group_');
      
      // 如果是群聊，直接返回，不更新未读计数
      if (isGroup) {
        return;
      }
      
      const normalizedId = normalizeId(targetId, isGroup);
      
      // 更新最近聊天列表
      const updateChatList = (list) => {
        const index = list.findIndex(item => extractAndNormalizeId(item) === normalizedId);
        if (index !== -1) {
          list[index].unreadCount = count;
        }
      };
      
      updateChatList(state.recentUsers);
      updateCombinedChats(state);
    },
    
    // 清除所有聊天记录
    CLEAR_ALL_CHATS(state) {
      state.recentChats = [];
      state.recentUsers = [];
      state.joinedGroups = [];
      state.currentChatId = null;
    }
  },
  actions: {
    // 获取群头像
    async fetchGroupAvatar({ rootState }, groupId) {
      try {
        const normalizedId = extractAndNormalizeId({ id: groupId, isGroup: true });
        const response = await axios.get(`${API_CONFIG.BASE_URL}/group/get-group-avatar/${normalizedId}`, {
          headers: { Authorization: `Bearer ${rootState.token}` }
        });
        return response.data || [];
      } catch (error) {
        console.error('获取群头像失败:', error);
        return [];
      }
    },

    // 加载最近聊天列表（只加载单聊）
    async loadRecentChats({ commit, rootState }) {
      try {
        const userId = rootState.user.id;
        const response = await axios.get(`${API_CONFIG.BASE_URL}/ws/chat/recent-chats/${userId}`, {
          headers: { Authorization: `Bearer ${rootState.token}` }
        });
        
        // 过滤掉群聊，只保留单聊
        const singleChats = (response.data || []).filter(chat => !chat.is_group);
        
        const formattedChats = singleChats.map(chat => {
          const normalizedId = extractAndNormalizeId(chat);
          
          return {
            id: normalizedId,
            normalizedId, // 添加规范化后的ID
            username: chat.target_username,
            photo: chat.target_photo,
            lastMessage: chat.last_message,
            lastMessageTime: chat.last_message_time,
            unreadCount: chat.unread_count || 0,
            isGroup: false
          };
        });
        
        commit('INIT_RECENT_CHATS', formattedChats);
        return formattedChats;
      } catch (error) {
        console.error('加载最近聊天列表失败:', error);
        return [];
      }
    },

    // 加载已加入的群聊
    async loadJoinedGroups({ commit, dispatch, rootState }) {
      try {
        if (!rootState.user?.id) {
          console.log('用户未登录，无法加载已加入的群聊');
          return [];
        }
        
        const response = await axios.get(
          `${API_CONFIG.BASE_URL}/group/get-joined-groups/${rootState.user.id}`,
          { headers: { Authorization: `Bearer ${rootState.token}` } }
        );
        
        // 并行获取所有群的头像
        const groupsWithAvatars = await Promise.all(
          (response.data || []).map(async group => {
            // 从多个可能的字段获取群ID
            const groupId = extractAndNormalizeId({ ...group, isGroup: true });
            const avatarMembers = await dispatch('fetchGroupAvatar', groupId);
            
            return {
              id: groupId,
              normalizedId: groupId, // 添加规范化后的ID
              username: group.name || '未命名群聊',
              photo: group.photo || null,
              target_id: groupId,
              created_at: group.created_at || new Date().toISOString(),
              unreadCount: group.unread_count || 0,
              members: group.members || [],
              membersCount: group.members_count || (group.members?.length || 0),
              ownerId: group.creator_id || null,
              avatar_members: avatarMembers
            };
          })
        );
        
        commit('INIT_JOINED_GROUPS', groupsWithAvatars);
        return groupsWithAvatars;
      } catch (error) {
        console.error('加载已加入的群聊失败:', error);
        ElMessage.error('加载已加入的群聊失败，请重试');
        return [];
      }
    },
    
    // 刷新单个群聊信息
    async refreshJoinedGroup({ commit, rootState }, groupId) {
      try {
        if (!rootState.user?.id) {
          console.log('用户未登录，无法刷新群聊信息');
          return null;
        }
        
        const normalizedId = extractAndNormalizeId({ id: groupId, isGroup: true });
        
        const response = await axios.get(`${API_CONFIG.BASE_URL}/group/${normalizedId}`, {
          headers: { Authorization: `Bearer ${rootState.token}` }
        });
        
        if (response.data) {
          const updatedGroup = {
            id: normalizedId,
            normalizedId, // 添加规范化后的ID
            ...response.data,
            isGroup: true
          };
          
          commit('UPDATE_JOINED_GROUP', updatedGroup);
          return updatedGroup;
        }
      } catch (error) {
        console.error(`刷新群聊 ${groupId} 信息失败:`, error);
        ElMessage.error('刷新群聊信息失败');
        return null;
      }
    },
    async dismissGroup({ commit, rootState }, groupId) {
  try {
    const normalizedId = extractAndNormalizeId({ id: groupId, isGroup: true });
    
    const response = await axios.post(
      `${API_CONFIG.BASE_URL}/group/dismiss`,
      { group_id: normalizedId },
      { headers: { Authorization: `Bearer ${rootState.token}` } }
    );
    
    if (response.data.success) {
      // 从已加入群组中移除该群组
      commit('REMOVE_JOINED_GROUP', normalizedId);
      
      // 清除当前选中的聊天ID（关键修复）
      commit('SET_CURRENT_CHAT_ID', null);
      
      return true;
    } else {
      throw new Error(response.data.message || '解散群聊失败');
    }
  } catch (error) {
    console.error('解散群聊失败:', error);
    ElMessage.error(error.response?.data?.detail || '解散群聊失败');
    throw error;
  }
},

async exitGroup({ commit, rootState }, groupId) {
  try {
    const normalizedId = extractAndNormalizeId({ id: groupId, isGroup: true });
    
    const response = await axios.post(
      `${API_CONFIG.BASE_URL}/group/exit`,
      { group_id: normalizedId },
      { headers: { Authorization: `Bearer ${rootState.token}` } }
    );
    
    if (response.data.success) {
      // 从已加入群组中移除该群组
      commit('REMOVE_JOINED_GROUP', normalizedId);
      
      // 清除当前选中的聊天ID（关键修复）
      commit('SET_CURRENT_CHAT_ID', null);
      
      return true;
    } else {
      throw new Error(response.data.message || '退出群聊失败');
    }
  } catch (error) {
    console.error('退出群聊失败:', error);
    ElMessage.error(error.response?.data?.detail || '退出群聊失败');
    throw error;
  }
},
    
    // 退出群聊
    // async exitGroup({ commit, rootState }, groupId) {
    //   try {
    //     const normalizedId = extractAndNormalizeId({ id: groupId, isGroup: true });
        
    //     const response = await axios.post(
    //       `${API_CONFIG.BASE_URL}/group/exit`,
    //       { group_id: normalizedId },
    //       { headers: { Authorization: `Bearer ${rootState.token}` } }
    //     );
        
    //     if (response.data.success) {
    //       // 从已加入群组中移除该群组
    //       commit('REMOVE_JOINED_GROUP', normalizedId);
    //       return true;
    //     } else {
    //       throw new Error(response.data.message || '退出群聊失败');
    //     }
    //   } catch (error) {
    //     console.error('退出群聊失败:', error);
    //     ElMessage.error(error.response?.data?.detail || '退出群聊失败');
    //     throw error;
    //   }
    // },
    
    // 保存最近聊天（只保存单聊）
    async saveRecentChat({ rootState }, chatInfo) {
      try {
        if (!rootState.user?.id) {
          console.log('用户未登录，无法保存最近聊天记录');
          return;
        }
        
        if (!chatInfo) {
          console.error('saveRecentChat 错误：未提供聊天用户信息');
          return;
        }
        
        const isGroup = chatInfo.isGroup === true;
        
        // 如果是群聊，直接返回，不保存到最近聊天
        if (isGroup) {
          return;
        }
        
        const userId = rootState.user.id;
        
        // 规范化ID
        const normalizedId = normalizeId(chatInfo.id, false);
        
        const recentChatData = {
          user_id: userId,
          target_id: normalizedId,
          target_username: chatInfo.username || '未知',
          target_photo: chatInfo.photo,
          last_message: chatInfo.lastMessage || '',
          last_message_time: chatInfo.lastMessageTime || new Date().toISOString(),
          unread_count: chatInfo.unreadCount || 0,
          is_group: false
        };
        
        await axios.post(`${API_CONFIG.BASE_URL}/ws/chat/recent-chats`, recentChatData, {
          headers: { Authorization: `Bearer ${rootState.token}` }
        });
      } catch (error) {
        console.error('保存最近聊天记录失败:', error);
        throw error;
      }
    },
    
    // 清除未读计数（只处理单聊）
    async clearUnreadCount({ commit, rootState }, targetId) {
      try {
        // 先判断是否为群聊ID（字符串且以group_开头）
        const isGroup = typeof targetId === 'string' && targetId.startsWith('group_');
        
        // 如果是群聊，直接返回，不清除未读计数
        if (isGroup) {
          return;
        }
        
        const normalizedId = normalizeId(targetId, isGroup);
        const userId = rootState.user.id;
        
        await axios.post(
          `${API_CONFIG.BASE_URL}/ws/chat/recent-chats/${userId}/clear-unread/${normalizedId}`, 
          {}, 
          { headers: { Authorization: `Bearer ${rootState.token}` } }
        );
        
        commit('UPDATE_UNREAD_COUNT', { targetId: normalizedId, count: 0 });
      } catch (error) {
        console.error('清除未读计数失败:', error);
        throw error;
      }
    },
    
    // 登出时清除所有聊天记录
    async clearAllChats({ commit }) {
      commit('CLEAR_ALL_CHATS');
    },
    
    // 手动添加聊天到最近聊天（只处理单聊）
    async addToRecent({ commit, dispatch }, chatInfo) {
      // 如果是群聊，直接返回
      if (chatInfo.isGroup === true) {
        return;
      }
      
      // 规范化ID
      const normalizedId = extractAndNormalizeId({ ...chatInfo, isGroup: false });
      const normalizedChatInfo = { ...chatInfo, id: normalizedId, normalizedId };
      
      commit('ADD_RECENT_CHAT', normalizedChatInfo);
      await dispatch('saveRecentChat', normalizedChatInfo);
    }
  },
  getters: {
    getRecentChats: state => state.recentChats,
    getRecentUsers: state => state.recentUsers,
    getJoinedGroups: state => state.joinedGroups,
    getCurrentChatId: state => state.currentChatId,
    
    getChatById: state => (id) => {
      const normalizedId = extractAndNormalizeId({ id });
      return state.recentChats.find(chat => extractAndNormalizeId(chat) === normalizedId);
    },
    
    getJoinedGroupById: state => (id) => {
      const normalizedId = extractAndNormalizeId({ id });
      return state.joinedGroups.find(group => extractAndNormalizeId(group) === normalizedId);
    },
    
    // 检查用户是否在指定群组中
    isUserInGroup: state => (groupId, userId) => {
      const normalizedId = extractAndNormalizeId({ id: groupId, isGroup: true });
      const group = state.joinedGroups.find(g => extractAndNormalizeId(g) === normalizedId);
      
      if (!group || !Array.isArray(group.members)) return false;
      return group.members.includes(userId);
    },
    
    getTotalUnreadCount: state => {
      return state.recentChats.reduce((total, chat) => total + (chat.unreadCount || 0), 0);
    },
    
    getJoinedGroupsCount: state => state.joinedGroups.length
  }
};

// 辅助函数：更新合并的聊天列表（只包含单聊）
function updateCombinedChats(state) {
  // 直接使用单聊列表，因为不再包含群聊
  state.recentChats = [...state.recentUsers].sort((a, b) => {
    const timeA = a.lastMessageTime ? new Date(a.lastMessageTime) : new Date(0);
    const timeB = b.lastMessageTime ? new Date(b.lastMessageTime) : new Date(0);
    return timeB - timeA;
  }).slice(0, 50);
}
export { extractAndNormalizeId, normalizeId };
export default chatModule;