<!-- src/components/GroupInfo.vue -->
<template>
  <div class="group-info-dialog" v-if="visible">
    <div class="group-info-content">
      <!-- 头部区域 -->
      <div class="group-info-header">
        <div class="group-info-close" @click="close">
          <i class="fa-solid fa-xmark"></i>
        </div>
        <div class="group-info-avatar">
          <div class="group-avatar">
            <div 
              v-for="(avatarUrl, idx) in groupAvatarUrls" 
              :key="idx"
              class="group-avatar-member"
              :style="getAvatarPosition(idx)"
            >
              <img 
                :src="getFullUrl(avatarUrl)" 
                alt="成员头像"
                @error="handleAvatarError"
              />
            </div>
          </div>
        </div>
        <div class="group-info-name">
          {{ groupInfo.group_name || '未命名群聊' }}
          <span class="group-info-edit" @click="showEditNameDialog" v-if="isGroupOwner">
            <i class="fa-solid fa-pen"></i>
          </span>
        </div>
        <div class="group-info-id">群ID: {{ groupInfo.group_id }}</div>
      </div>
      
      <!-- 可滚动的内容区域 -->
      <div class="group-info-body">
        <!-- 群成员区域 -->
        <div class="group-info-section">
          <div class="group-info-section-title">群成员 ({{ groupInfo.members_count || 0 }})</div>
          <div class="members-list">
            <div 
              class="member-item" 
              v-for="member in validGroupMembers" 
              :key="getMemberKey(member)"
              @mouseover="hoverMemberId = getMemberId(member)"
              @mouseleave="hoverMemberId = null"
            >
              <div class="member-avatar-container">
                <div class="member-avatar">
                  <img :src="getMemberAvatar(member)" alt="成员头像" @error="handleAvatarError">
                </div>
                <!-- 移除按钮 -->
                <div 
                  class="member-remove-action" 
                  v-if="isGroupOwner && canRemoveMember(member)"
                  @click.stop="removeMember(member)"
                >
                  <i class="fa-solid fa-minus"></i>
                </div>
              </div>
              <div class="member-name">{{ getMemberName(member) }}</div>
              <div class="member-role">{{ getMemberRole(member) }}</div>
            </div>
            
            <!-- 添加成员按钮 -->
            <div class="member-item">
              <div class="member-avatar-container">
                <div class="add-member-btn" @click="showAddMemberDialog">
                  <i class="fa-solid fa-plus"></i>
                </div>
              </div>
              <div class="member-name">添加成员</div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 固定的操作按钮区域 -->
      <div class="group-info-actions">
        <div class="group-action-btn" @click="toggleMute">
          <i class="fa-solid" :class="isMuted ? 'fa-bell' : 'fa-bell-slash'"></i> 
          {{ isMuted ? '开启通知' : '消息免打扰' }}
        </div>

        <!-- 群主转让按钮 - 只有群主可见 -->
        <div 
          class="group-action-btn transfer-action" 
          @click="showTransferDialog"
          v-if="isGroupOwner"
        >
          <i class="fa-solid fa-crown"></i> 
          转让群主
        </div>

        <div 
          class="group-action-btn danger-action" 
          @click="isGroupOwner ? dismissGroup() : exitGroup()"
        >
          <i class="fa-solid" :class="isGroupOwner ? 'fa-trash' : 'fa-right-from-bracket'"></i> 
          {{ isGroupOwner ? '解散群聊' : '退出群聊' }}
        </div>
      </div>
    </div>

    <!-- 编辑群名称弹窗 -->
    <div v-if="showEditName" class="edit-name-dialog">
      <div class="edit-name-content">
        <div class="edit-name-title">修改群名称</div>
        <input 
          type="text" 
          class="edit-name-input" 
          v-model="editGroupName" 
          placeholder="请输入群名称"
          maxlength="20"
        >
        <div class="edit-name-buttons">
          <button class="edit-name-btn edit-name-cancel" @click="cancelEditName">取消</button>
          <button class="edit-name-btn edit-name-confirm" @click="confirmEditName">确定</button>
        </div>
      </div>
    </div>

    <!-- 添加成员弹窗 -->
    <div v-if="showAddMember" class="add-member-dialog">
      <div class="add-member-content">
        <div class="add-member-header">
          <div class="add-member-title">添加成员</div>
          <div class="add-member-close" @click="closeAddMemberDialog">
            <i class="fa-solid fa-xmark"></i>
          </div>
        </div>
        <div class="add-member-search">
          <input 
            type="text" 
            v-model="searchKeyword" 
            placeholder="搜索用户ID、用户名、电话或邮箱..."
            class="search-input"
            @input="handleSearchInput"
          >
        </div>
        <div 
          class="add-member-list" 
          ref="userListRef" 
          @scroll="handleUserListScroll"
          :class="{ 'no-scroll': !pagination.hasMore && !pagination.loading }"
        >
          <div 
            v-for="user in filteredUsers" 
            :key="user.id" 
            class="user-item"
            :class="{ 'user-item-disabled': isUserInGroup(user.id) }"
            @click="!isUserInGroup(user.id) && selectUser(user)"
          >
            <div class="user-avatar">
              <img :src="getFullUrl(user.photo)" alt="用户头像" @error="handleAvatarError">
            </div>
            <div class="user-info">
              <div class="user-name">{{ user.username }}</div>
              <div class="user-contact">
                <span v-if="user.phone">{{ user.phone }}</span>
                <span v-if="user.email"> | {{ user.email }}</span>
              </div>
            </div>
            <div class="user-checkbox">
              <input 
                type="checkbox" 
                :checked="isUserSelected(user.id)" 
                :disabled="isUserInGroup(user.id)"
              >
              <div class="user-in-group-tag" v-if="isUserInGroup(user.id)">已在群中</div>
            </div>
          </div>
          <div class="no-users" v-if="filteredUsers.length === 0 && !pagination.loading">
            {{ searchKeyword ? '未找到匹配的用户' : '暂无用户数据' }}
          </div>
          <div class="loading-more" v-if="pagination.loading">
            <i class="fa-solid fa-spinner fa-spin"></i> 加载中...
          </div>
          <div class="no-more" v-if="!pagination.hasMore && filteredUsers.length > 0">
            没有更多用户了
          </div>
        </div>
        <div class="add-member-footer">
          <div class="selected-count">已选择: {{ selectedCount }} 人</div>
          <div class="add-member-buttons">
            <button class="add-member-cancel" @click="closeAddMemberDialog">取消</button>
            <button 
              class="add-member-confirm" 
              @click="confirmAddMembers"
              :disabled="selectedCount === 0"
            >确认添加</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 群主转让弹窗 -->
    <div v-if="showTransfer" class="transfer-dialog">
      <div class="transfer-content">
        <div class="transfer-header">
          <div class="transfer-title">转让群主身份</div>
          <div class="transfer-close" @click="closeTransferDialog">
            <i class="fa-solid fa-xmark"></i>
          </div>
        </div>
        
        <div class="transfer-warning">
          <i class="fa-solid fa-exclamation-triangle"></i>
          <p>转让后您将失去群主身份，无法撤销此操作</p>
        </div>
        
        <div class="transfer-search">
          <input 
            type="text" 
            v-model="transferSearchKeyword" 
            placeholder="搜索群成员..."
            class="transfer-search-input"
            @input="handleTransferSearch"
          >
        </div>
        
        <div class="transfer-members-list" ref="transferListRef">
          <div 
            v-for="member in filteredTransferMembers" 
            :key="getMemberKey(member)" 
            class="transfer-member-item"
            @click="selectTransferMember(member)"
            :class="{ 
              'selected': isTransferMemberSelected(member),
              'transfer-member-item-disabled': isCurrentUser(member)
            }"
          >
            <div class="transfer-member-avatar">
              <img :src="getMemberAvatar(member)" alt="成员头像" @error="handleAvatarError">
            </div>
            <div class="transfer-member-info">
              <div class="transfer-member-name">{{ getMemberName(member) }}</div>
              <div class="transfer-member-role">{{ getMemberRole(member) }}</div>
            </div>
            <div class="transfer-member-select">
              <i 
                class="fa-solid fa-check" 
                v-if="isTransferMemberSelected(member)"
              ></i>
            </div>
            <div class="transfer-member-disabled-tag" v-if="isCurrentUser(member)">
              当前用户
            </div>
          </div>
          
          <div class="no-transfer-members" v-if="filteredTransferMembers.length === 0 && !transferLoading">
            {{ transferSearchKeyword ? '未找到匹配的群成员' : '暂无群成员数据' }}
          </div>
          
          <div class="transfer-loading" v-if="transferLoading">
            <i class="fa-solid fa-spinner fa-spin"></i> 加载中...
          </div>
        </div>
        
        <div class="transfer-footer">
          <div class="selected-member-info" v-if="selectedTransferMember">
            已选择: {{ getMemberName(selectedTransferMember) }}
          </div>
          <div class="transfer-buttons">
            <button class="transfer-cancel" @click="closeTransferDialog">取消</button>
            <button 
              class="transfer-confirm" 
              @click="confirmTransfer"
              :disabled="!selectedTransferMember"
            >确认转让</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>


<script>
import { ref, computed, onMounted, watch, nextTick  } from 'vue';
import { useRoute, useRouter } from 'vue-router'; // 添加 useRouter 导入
import { useStore } from 'vuex';
import { ElMessage, ElMessageBox } from 'element-plus';
import 'element-plus/es/components/message-box/style/css';
import 'element-plus/es/components/message/style/css';
import axios from 'axios';
import { API_CONFIG } from '@/config/config';
import defaultAvatar from '@/assets/default-avatar.png';
import { extractAndNormalizeId } from '@/store/modules/chat'; // 导入辅助函数
import _ from 'lodash';

export default {
  name: 'GroupInfo',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    groupInfo: {
      type: Object,
      default: () => ({})
    }
  },
  emits: ['update:visible', 'group-updated', 'group-exited'],
  setup(props, { emit }) {
    const store = useStore();
    const currentUserId = computed(() => store.state.user.id);
    const currentUser = computed(() => store.state.user);
    const router = useRouter(); // 正确初始化 router
    const route = useRoute();
    const groupMembers = ref([]);
    const isMuted = ref(false);
    const showEditName = ref(false);
    const editGroupName = ref('');
    const showAddMember = ref(false);
    const searchKeyword = ref('');
    const selectedUserIds = ref(new Set());
    const allUsers = ref([]);
    const hoverMemberId = ref(null);
    const userListRef = ref(null); // 添加用户列表的引用
    const systemNotifications = ref([]); 

    const showTransfer = ref(false);
    const transferSearchKeyword = ref('');
    const selectedTransferMember = ref(null);
    const transferMembers = ref([]);
    const transferDialogRef = ref(null);
    // 分页控制
    const pagination = ref({
      page: 1,
      pageSize: 10,
      total: 0,
      loading: false,
      hasMore: true
    });

    const isGroupOwner = computed(() => {
      return props.groupInfo.creator_id === currentUserId.value;
    });
    // 处理头像加载错
    const handleAvatarError = (event) => {
      event.target.src = defaultAvatar;
    };

const formatNotificationTime = (notification) => {
  const time = notification.created_at || notification.time;
  if (!time) return '';
  
  try {
    const date = new Date(time);
    return date.toLocaleDateString('zh-CN');
  } catch (error) {
    return '';
  }
};

// 过滤可转让的成员（排除自己）
const filteredTransferMembers = computed(() => {
  let members = transferMembers.value;
  
  if (transferSearchKeyword.value) {
    const keyword = transferSearchKeyword.value.toLowerCase();
    members = members.filter(member => 
      getMemberName(member).toLowerCase().includes(keyword)
    );
  }
  
  return members.filter(member => {
    const memberId = typeof member === 'number' ? member : member.id;
    return memberId !== currentUserId.value; // 排除自己
  });
});

// 显示转让弹窗
    // 修改后的showTransferDialog方法
    const showTransferDialog = async () => {
      console.log("显示转让弹窗，当前群信息:", props.groupInfo);
      
      try {
        // 直接设置为true
        showTransfer.value = true;
        transferSearchKeyword.value = '';
        selectedTransferMember.value = null;
        
        console.log("当前用户ID:", currentUserId.value);
        
        // 等待DOM更新
        await nextTick();
        
        // 安全的DOM检查
        if (transferDialogRef.value) {
          console.log("弹窗元素已渲染:", transferDialogRef.value);
          console.log("弹窗显示状态:", window.getComputedStyle(transferDialogRef.value).display);
        } else {
          console.log("弹窗元素尚未渲染");
        }
        
        // 加载可转让的成员列表
        await loadTransferMembers();
        
        console.log("转让弹窗状态:", showTransfer.value);
        console.log("加载到的可转让成员:", transferMembers.value);
        
      } catch (error) {
        console.error("显示转让弹窗时出错:", error);
      }
    };

// 关闭转让弹窗
const closeTransferDialog = () => {
  showTransfer.value = false;
};

const loadTransferMembers = async () => {
  try {
    // 使用现有的群成员数据，过滤掉自己
    transferMembers.value = validGroupMembers.value.filter(member => {
      const memberId = typeof member === 'number' ? member : member.id;
      return memberId !== currentUserId.value;
    });
    console.log("加载到的可转让成员:", transferMembers.value);
  } catch (error) {
    console.error('加载转让成员失败:', error);
    ElMessage.error('加载成员列表失败');
  }
};
// 选择转让成员
const selectTransferMember = (member) => {
  selectedTransferMember.value = member;
};
console.log("选中的转让成员:", selectedTransferMember.value);
// 确认转让群主
const confirmTransfer = async () => {
  if (!selectedTransferMember.value) {
    ElMessage.warning('请选择要转让的成员');
    return;
  }
  
  const memberId = typeof selectedTransferMember.value === 'number' 
    ? selectedTransferMember.value 
    : selectedTransferMember.value.id;
  
  const memberName = getMemberName(selectedTransferMember.value);
  
  try {
    // 确认对话框
    await ElMessageBox.confirm(
      `确定要将群主身份转让给 ${memberName} 吗？此操作不可撤销`,
      '确认转让',
      { 
        type: 'warning',
        confirmButtonText: '确定转让',
        cancelButtonText: '取消'
      }
    );
    
    // 调用转让API
    const response = await axios.post(
      `${API_CONFIG.BASE_URL}/group/transfer-ownership`,
      {
        group_id: props.groupInfo.group_id,
        new_owner_id: memberId
      },
      { 
        headers: { 
          Authorization: `Bearer ${store.state.token}` 
        },
        timeout: 10000
      }
    );
    
    if (response.data.success) {
      ElMessage.success('群主转让成功');
      
      // 发送系统消息
      await sendSystemMessage(
        props.groupInfo.group_id,
        `${store.state.user.username} 将群主身份转让给 ${memberName}`,
        'transfer_ownership'
      );
      
      // 关闭弹窗
      closeTransferDialog();
      
      // 触发刷新
      refreshSystemMessages();
      emit('group-updated');
      
      // 关闭群信息面板
      close();
      
    } else {
      ElMessage.error(response.data.message || '转让失败');
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('转让群主失败:', error);
      ElMessage.error('转让失败');
    }
  }
};

// 搜索处理
const handleTransferSearch = _.debounce(() => {
  // 搜索逻辑已经在filteredTransferMembers计算属性中实现
}, 300);



    // 添加获取成员ID的方法
    const getMemberId = (member) => {
      if (!member) return null;
      return typeof member === 'number' ? member : member.id;
    };
    // 计算属性：有效的群组成员
    const validGroupMembers = computed(() => {
      return (groupMembers.value || []).filter(member => 
        member && 
        (typeof member === 'object' || typeof member === 'number') &&
        (member.id !== undefined || typeof member === 'number')
      );
    });
    console.log("有效的群组成员:", validGroupMembers.value);

    const groupAvatarUrls = computed(() => {
      console.log("计算群头像，当前群信息:", props.groupInfo);

      if (!props.groupInfo) return [defaultAvatar];
      
      const avatarMembers = props.groupInfo.avatar_members || [];
      
      // 优先使用 avatar_members
      if (avatarMembers.length > 0) {
        return avatarMembers
          .slice(0, 9)
          .map(url => getFullUrl(url))
          .filter(Boolean);
      }
      
      // 如果没有 avatar_members，使用群成员的头像
      if (groupMembers.value && groupMembers.value.length > 0) {
        return groupMembers.value
          .slice(0, 9)
          .map(member => {
            if (typeof member === 'object' && member.photo) {
              return getFullUrl(member.photo);
            }
            return defaultAvatar;
          });
      }
      
      // 如果都没有，使用默认头像
      return [defaultAvatar];
    });


    const filteredUsers = computed(() => {
      if (!searchKeyword.value) return allUsers.value;
      
      const keyword = searchKeyword.value.toLowerCase();
      return allUsers.value.filter(user => 
        user && (
          (user.username && user.username.toLowerCase().includes(keyword)) ||
          (user.phone && user.phone.includes(keyword)) ||
          (user.email && user.email.toLowerCase().includes(keyword)) ||
          (user.id && user.id.toString().includes(keyword))
        )
      );
    });
     
    // 检查用户是否已在群中
    const isUserInGroup = (userId) => {
      return validGroupMembers.value.some(member => {
        const memberId = typeof member === 'object' ? member.id : member;
        return memberId === userId;
      });
    };

    const handleUserListScroll = () => {
      if (!userListRef.value || pagination.value.loading || !pagination.value.hasMore) {
        return;
      }

      const list = userListRef.value;
      const scrollTop = list.scrollTop;
      const scrollHeight = list.scrollHeight;
      const clientHeight = list.clientHeight;

      // 当滚动到底部时加载更多
      if (scrollTop + clientHeight >= scrollHeight - 50) {
        loadAllUsers();
      }
    };

    const getFullUrl = (path) => {
      if (!path) return defaultAvatar;
      return path.startsWith('http') ? path : `${API_CONFIG.BASE_URL}${path}`;
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

    const getMemberAvatar = (member) => {
      if (!member) return defaultAvatar;
      
      if (typeof member === 'number') {
        return defaultAvatar;
      }
      
      if (!member.photo) {
        return defaultAvatar;
      }
      
      return getFullUrl(member.photo);
    };

    const getMemberRole = (member) => {
      if (!member) return '成员';
      
      const memberId = typeof member === 'number' ? member : member.id;
      
      if (memberId === props.groupInfo.creator_id) return '群主';
      return '成员';
    };

    const getMemberName = (member) => {
      if (!member) return '未知用户';
      if (typeof member === 'number') return `用户 ${member}`;
      return member.username || `用户 ${member.id}`;
    };

    const getMemberKey = (member) => {
      if (typeof member === 'number') return member;
      if (member && member.id) return member.id;
      return Math.random();
    };

      // 计算属性：选中用户数量
    const selectedCount = computed(() => selectedUserIds.value.size );

    const canRemoveMember = (member) => {
      
      if (!member) return false;
      const memberId = typeof member === 'number' ? member : member.id;
      
      if (!memberId) return false;
      if (memberId === currentUserId.value) return false;
      if (memberId === props.groupInfo.creator_id) return false;
    
      
      return true;
    };

    const close = () => {
      emit('update:visible', false);
    };

    const loadGroupMembers = async () => {
      try {
        const response = await axios.get(
          `${API_CONFIG.BASE_URL}/group/${props.groupInfo.group_id}/members`,
          { headers: { Authorization: `Bearer ${store.state.token}` } }
        );
        
        if (response.data) {
          const membersData = response.data.group_members || [];
          console.log("加载到的群成员数据:", membersData);
          if (Array.isArray(membersData) && membersData.length > 0) {
            if (typeof membersData[0] === 'number') {
              // 如果是ID数组，转换为成员对象
              groupMembers.value = membersData.map(id => ({
                id: id,
                username: `用户 ${id}`,
                photo: null,
              }));
            } else {
              // 已经是完整的成员对象
              groupMembers.value = membersData.filter(member => 
                member && typeof member === 'object' && member.id !== undefined
              );
            }
          } else {
            groupMembers.value = [];
          }
        }
      } catch (error) {
        console.error('加载群成员失败:', error);
        ElMessage.error('加载群成员失败');
      }
    };

  // 检查当前群组是否有效
    const checkGroupValidity = async () => {
      const groupId = route.params.id;
      if (!groupId) return;
      
      // 检查是否是群聊ID
      const isGroup = typeof groupId === 'string' && groupId.startsWith('group_');
      if (!isGroup) return;
      
      // 检查用户是否还在这个群组中
      const joinedGroups = store.getters['chat/getJoinedGroups'];
      const groupExists = joinedGroups.some(group => 
        extractAndNormalizeId(group) === extractAndNormalizeId({ id: groupId, isGroup: true })
      );
      
      if (!groupExists) {
        // 群组不存在或用户已退出，重定向到聊天列表
        ElMessage.warning('您已退出该群组或群组不存在');
        router.push('/chats');
      }
    };
    
    // 加载所有用户（从/user/get-users接口）
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
        });

        console.log("加载到的所有用户数据:", response.data);
        
        if (response.data && Array.isArray(response.data.data)) {
          const memberIds = new Set(validGroupMembers.value.map(m => 
            typeof m === 'number' ? m : m.id
          ));
          
          const newUsers = response.data.data.filter(user => 
            user && user.id && !memberIds.has(user.id)
          );
          
          // 合并用户列表
          allUsers.value = [...allUsers.value, ...newUsers];
          
          // 更新分页信息
          pagination.value.total = response.data.total || 0;
          pagination.value.hasMore = allUsers.value.length < pagination.value.total;
          
          if (pagination.value.hasMore) {
            pagination.value.page += 1;
          }
          
          console.log("过滤后的可添加用户列表:", allUsers.value);
        }
      } catch (error) {
        console.error('加载用户列表失败:', error);
        ElMessage.error('加载用户列表失败');
      } finally {
        pagination.value.loading = false;
      }
    };

        // 搜索输入防抖处理
    const handleSearchInput = _.debounce(() => {
      // 搜索逻辑已经在filteredUsers计算属性中实现
    }, 300);

    const showEditNameDialog = () => {
      editGroupName.value = props.groupInfo.group_name || '';
      showEditName.value = true;
    };

    const cancelEditName = () => {
      showEditName.value = false;
    };

    const confirmEditName = async () => {
      try {
        const response = await axios.post(
          `${API_CONFIG.BASE_URL}/group/update-name`,
          {
            group_id: props.groupInfo.group_id,
            name: editGroupName.value
          },
          { headers: { Authorization: `Bearer ${store.state.token}` } }
        );
        
        if (response.data.success) {
          ElMessage.success('群名称修改成功');
      // 4. 关闭添加成员弹窗
      closeAddMemberDialog();

          // 1. 创建系统通知对象
      const newNotification = {
        id: `system_${Date.now()}`, // 生成唯一ID
        type: "system_message",
        message_type: "system",
        to: props.groupInfo.group_id,
        content: `${store.state.user.username} 将群名称修改为 "${editGroupName.value}"`,
        from: store.state.user.id,
        from_username: store.state.user.username,
        timestamp: Date.now(),
        action: "update_group_name", // 对应修改群名的动作类型
        is_system: true,
        time: new Date().toISOString() // 保持与后端一致的时间格式
      };
            
      // 3. 可选：限制通知数量，避免数组过大
      if (systemNotifications.value.length > 100) {
        systemNotifications.value.pop(); // 移除最旧的通知
      }


          showEditName.value = false;
          
          // 更新Vuex store中的群组信息
          store.commit('chat/UPDATE_JOINED_GROUP', {
            group_id: props.groupInfo.group_id,
            name: editGroupName.value,
            ...props.groupInfo
          });
          
          emit('group-updated');
          emit('update:visible', false);
      


      // 发送系统消息：用户修改了群名称
      await sendSystemMessage(
        props.groupInfo.group_id,
        newNotification.content,
        'update_group_name'
      );
                // 触发刷新系统消息
      refreshSystemMessages();

      console.log("系统通知更新:", systemNotifications.value);

        } else {
          ElMessage.error(response.data.message || '修改失败');
          showEditName.value = false;
        }
      } catch (error) {
        console.error('修改群名称失败:', error);
        ElMessage.error('修改群名称失败');
        showEditName.value = false;
      }
    };

    const toggleMute = async () => {
      try {
        const response = await axios.post(
          `${API_CONFIG.BASE_URL}/group/${props.groupInfo.group_id}/mute?user_id=${currentUserId.value}`,
          { muted: !isMuted.value, user_id: currentUserId.value },
          { headers: { Authorization: `Bearer ${store.state.token}` } }
        );
        
        if (response.data.success) {
          isMuted.value = !isMuted.value;
          ElMessage.success(isMuted.value ? '已开启消息免打扰' : '已关闭消息免打扰');
        }
      } catch (error) {
        console.error('设置消息免打扰失败:', error);
        ElMessage.error('设置失败');
      }
    };

      const removeMember = async (member) => {
        if (!member) {
          ElMessage.error('成员信息无效');
          return;
        }
        
        const memberId = typeof member === 'number' ? member : member.id;
        const memberName = typeof member === 'number' ? `用户 ${member}` : (member.username || `用户 ${member.id}`);
        
        try {
          // 确认对话框
          await ElMessageBox.confirm(
            `确定要将 ${memberName} 移出群聊吗？`,
            '确认移除',
            { 
              type: 'warning',
              confirmButtonText: '确定移除',
              cancelButtonText: '取消'
            }
          );
          
          // 调用API移除成员
          const response = await axios.post(
            `${API_CONFIG.BASE_URL}/group/remove-member`,
            {
              group_id: props.groupInfo.group_id,
              user_id: memberId
            },
            { 
              headers: { 
                Authorization: `Bearer ${store.state.token}` 
              },
              timeout: 10000
            }
          );

          if (response.data.success) {
            ElMessage.success('成员已移除');

            // 重新加载群成员
            await loadGroupMembers();
            
            // 重新加载可添加的用户列表
            await loadAllUsers();
            
            // 发送系统消息
            await sendSystemMessage(
              props.groupInfo.group_id,
              `${store.state.user.username} 将 ${memberName} 移出群聊`,
              'remove_member'
            );
            
            // 触发刷新系统消息
            refreshSystemMessages();
            
            // 通知父组件更新
            emit('group-updated');
            
            // 关闭弹窗
            close();

          } else {
            ElMessage.error(response.data.message || '移除成员失败');
          }
        } catch (error) {
          if (error !== 'cancel') {
            console.error('移除成员失败:', error);
            ElMessage.error('移除成员失败');
          }
        }
      };
// 添加一个方法来触发父组件刷新系统消息
const refreshSystemMessages = () => {
  // 通过事件触发父组件刷新系统消息
  emit('refresh-system-messages');
};

// 解散群聊
const dismissGroup = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要解散该群聊吗？解散后所有成员将被移除，且无法恢复',
      '确认解散',
      { 
        type: 'warning',
        confirmButtonText: '确定解散',
        cancelButtonText: '取消'
      }
    );
    
    const response = await axios.post(
      `${API_CONFIG.BASE_URL}/group/dismiss`,
      { group_id: props.groupInfo.group_id },
      { headers: { Authorization: `Bearer ${store.state.token}` } }
    );
    
    if (response.data.success) {
      ElMessage.success('群聊已解散');
      // 4. 关闭添加成员弹窗
      closeAddMemberDialog();

      const newNotification = {
        id: `system_${Date.now()}`, // 生成唯一ID
        type: "system_message",
        message_type: "system",
        to: props.groupInfo.group_id,
        content: `${store.state.user.username} 解散了群聊 "${props.groupInfo.group_name || '未命名群聊'}"`,
        from: store.state.user.id,
        from_username: store.state.user.username,
        timestamp: Date.now(),
        action: "dismiss_group", // 对应修改群名的动作类型
        is_system: true,
        time: new Date().toISOString() // 保持与后端一致的时间格式
      };

      // 从已加入群组中移除该群组
      store.commit('chat/REMOVE_JOINED_GROUP', props.groupInfo.group_id);
      close();
      emit('group-exited');
      
      // 重定向到聊天列表
      router.push('/chats');

      // 解散群后

      await sendSystemMessage(
        props.groupInfo.group_id,
        newNotification.content,
        'dismiss_group'
      );
      
            // 触发刷新系统消息
      refreshSystemMessages();
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('解散群聊失败:', error);
      
      // 详细的错误处理
      if (error.response) {
        const status = error.response.status;
        if (status === 403) {
          ElMessage.error('没有权限解散群聊');
        } else if (status === 404) {
          ElMessage.error('群组不存在');
        } else if (status === 400) {
          if (error.response.data?.detail?.includes("群组已被解散")) {
            ElMessage.error('群组已被解散');
          } else {
            ElMessage.error(error.response.data?.detail || '请求参数错误');
          }
        } else {
          ElMessage.error(error.response.data?.message || '解散群聊失败');
        }
      } else {
        ElMessage.error('解散群聊失败');
      }
    }
  }
};

// 退出群聊
const exitGroup = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要退出该群聊吗？退出后将不再接收该群消息',
      '确认退出',
      { type: 'warning' }
    );
    
    await store.dispatch('chat/exitGroup', props.groupInfo.group_id);
    
    // 清除当前选中的聊天ID（关键修复）
    
    ElMessage.success('已退出群聊');
            // 4. 关闭添加成员弹窗
            closeAddMemberDialog();

      const newNotification = {
        id: `system_${Date.now()}`, // 生成唯一ID
        type: "system_message",
        message_type: "system",
        to: props.groupInfo.group_id,
        content: `${store.state.user.username} 已退出群聊`,
        from: store.state.user.id,
        from_username: store.state.user.username,
        timestamp: Date.now(),
        action: "exit_group", // 对应修改群名的动作类型
        is_system: true,
        time: new Date().toISOString() // 保持与后端一致的时间格式
      };


    close();
    emit('group-exited');
    
    // 重定向到聊天列表
    router.push('/chats');

    // 发送系统消息：用户退出群聊
    await sendSystemMessage(
      props.groupInfo.group_id,
      newNotification.content,
      'exit_group'
    );
          // 触发刷新系统消息
      refreshSystemMessages();

  } catch (error) {
    if (error !== 'cancel') {
      console.error('退出群聊失败:', error);
    }
  }
};

    const showAddMemberDialog = async () => {
      console.log("显示添加成员弹窗");
      
      // 重置分页和用户列表
      pagination.value = {
        page: 1,
        pageSize: 20,
        total: 0,
        loading: false,
        hasMore: true
      };
      allUsers.value = [];
      selectedUserIds.value.clear();
      searchKeyword.value = '';
      
      showAddMember.value = true;
      
      // 等待DOM更新后加载第一页数据
      await nextTick();
      await loadAllUsers();
      
      console.log("所有用户列表大小: ", selectedUserIds.value.size);
    };

    const closeAddMemberDialog = () => {
      showAddMember.value = false;
    };

    const selectUser = (user) => {
      console.log("选择用户:", selectedUserIds.value);
      console.log("选择用户对象:", selectedUserIds.value.size + 1);
      if (selectedUserIds.value.has(user.id)) {
        selectedUserIds.value.delete(user.id);
      } else {
        selectedUserIds.value.add(user.id);
      }
    };

    const isUserSelected = (userId) => {
      return selectedUserIds.value.has(userId);
    };

// 发送系统消息的函数 - HTTP版本
const sendSystemMessage = async (groupId, content, actionType = 'system') => {
  try {
    console.log("准备发送系统消息，群组:", groupId);
    
    const systemMessage = {
      type: 'system_message', // 系统消息类型
      to: groupId,
      content: content,
      from: store.state.user.id,
      from_username: store.state.user.username,
      message_type: 'system',
      id: Date.now(),
      action: actionType, // 动作类型：add_members, remove_member, dismiss_group, exit_group
    };
    
    console.log('系统消息内容:', systemMessage);
    
    const response = await axios.post(
      `${API_CONFIG.BASE_URL}/group/system-message`,
      systemMessage,
      {
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${store.state.token}`
        },
        timeout: 10000 // 10秒超时
      }
    );
    
    console.log('系统消息发送成功:', response.data);
    return response.data;
    
  } catch (error) {
    console.error('发送系统消息失败:', error);
    
    // 不阻止主流程，只是记录错误
    if (error.response) {
      // 服务器返回错误
      console.error('服务器错误:', error.response.data);
    } else if (error.request) {
      // 网络错误
      console.error('网络错误:', error.message);
    } else {
      // 其他错误
      console.error('错误:', error.message);
    }
    
    // 仍然resolve，不阻止主流程
    return { status: 'error', message: '发送失败但继续流程' };
  }
};


// 加载群历史系统通知
const loadSystemNotifications = async () => {
  try {
    // 确保群ID存在
    if (!props.groupInfo.group_id) return;
    
    const response = await axios.get(
      `${API_CONFIG.BASE_URL}/group/${props.groupInfo.group_id}/system-message`, // 后端需提供该接口
      { headers: { Authorization: `Bearer ${store.state.token}` } }
    );

    console.log("加载到的群通知数据: ", response.data);
    
    // 校验接口返回数据（需与后端约定格式，匹配模板中使用的字段）
    if (response.data && Array.isArray(response.data)) {
      // 过滤出“系统通知”（避免混入普通消息），并按时间倒序排列（最新的在最上面）
      const systemMsgs = response.data
        .filter(msg => msg.message_type === 'system' && msg.is_system) // 匹配你定义的系统消息标识
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
        console.log("过滤后的群通知:1 ", systemMsgs);


    } else {
      systemNotifications.value = [];
    }
  } catch (error) {
    console.error('加载群通知失败:', error);
    systemNotifications.value = [];
  }
};


      const confirmAddMembers = async () => {
        if (selectedUserIds.value.size === 0) {
          ElMessage.warning('请选择要添加的成员');
          return;
        }

        try {
          const response = await axios.post(
            `${API_CONFIG.BASE_URL}/group/add-members`,
            {
              group_id: props.groupInfo.group_id,
              user_ids: Array.from(selectedUserIds.value)
            },
            { headers: { Authorization: `Bearer ${store.state.token}` } }
          );
          
          if (response.data.success) {
            ElMessage.success('成员添加成功');
            // 4. 关闭添加成员弹窗
            closeAddMemberDialog();

            // 获取添加的用户名列表
          const addedUserNames = allUsers.value
            .filter(user => selectedUserIds.value.has(user.id))
            .map(user => user.username)
            .join('、');
            console.log("添加的用户名列表: ", addedUserNames);

            const newNotification = {
              id: `system_${Date.now()}`, // 生成唯一ID
              type: "system_message",
              message_type: "system",
              to: props.groupInfo.group_id,
              content: `${store.state.user.username} 邀请 ${addedUserNames} 加入群聊`,
              from: store.state.user.id,
              from_username: store.state.user.username,
              timestamp: Date.now(),
              action: "add_members", // 对应修改群名的动作类型
              is_system: true,
              time: new Date().toISOString() // 保持与后端一致的时间格式
            };

            // 1. 重新加载群成员信息
            await loadGroupMembers();
            
            // 2. 重新加载可添加的用户列表
            await loadAllUsers();
                     

            console.log("系统通知 == 开始发送 群添加成员到群消息通知 ： ",newNotification.content );
          // 发送系统消息：用户邀请成员加入群聊
          await sendSystemMessage(
            props.groupInfo.group_id,
            newNotification.content,
            'add_members'
          );
            
                // 触发刷新系统消息
             refreshSystemMessages();
            
            // 5. 通知父组件更新
            emit('group-updated');
            
            // 6. 立即返回聊天界面
            emit('update:visible', false);
            
            // 7. 触发聊天界面刷新
            store.commit('chat/SET_CURRENT_CHAT_ID', props.groupInfo.group_id);
            
          }
        } catch (error) {
          console.error('添加成员失败:', error);
          ElMessage.error('添加成员失败');
        }
      };

      

    watch(() => props.visible, async (newVisible) => {
      console.log("群信息弹窗可见性变化:", newVisible, props.groupInfo);
      if (newVisible && props.groupInfo.group_id) {
        await loadGroupMembers();
        console.log("群信息变化，重新加载成员:", props.groupInfo);
        await checkGroupValidity();
        
        try {
          const response = await axios.get(
            `${API_CONFIG.BASE_URL}/group/${props.groupInfo.group_id}/mute-status?user_id=${currentUserId.value}`,
            { headers: { Authorization: `Bearer ${store.state.token}` } }
          );
          
          if (response.data.success) {
            isMuted.value = response.data.muted;
          }
        } catch (error) {
          console.error('获取免打扰状态失败:', error);
        }
      }
    });

    // 监听路由变化
    watch(() => route.params.id, (newId) => {
      if (newId) {
        checkGroupValidity();
         loadSystemNotifications(); // 新增：加载通知
         console.log("路由变化，检查群有效性:", newId);
      }
    });

    onMounted(async () => {
      if (props.visible && props.groupInfo.group_id) {
        await loadGroupMembers();
        await checkGroupValidity();
         await loadSystemNotifications(); // 新增：加载通知
        try {
          const response = await axios.get(
            `${API_CONFIG.BASE_URL}/group/${props.groupInfo.group_id}/mute-status?user_id=${currentUserId.value}`,
            { headers: { Authorization: `Bearer ${store.state.token}` } }
          );
          
          if (response.data.success) {
            isMuted.value = response.data.muted;
          }
        } catch (error) {
          console.error('获取免打扰状态失败:', error);
        }
      }
    });

    return {
      currentUserId,
      groupMembers,
      validGroupMembers,
      currentUser,
      isMuted,
      showEditName,
      handleAvatarError,
      editGroupName,
      showAddMember,
      formatNotificationTime,
      searchKeyword,
      filteredUsers,
      isGroupOwner,
      handleUserListScroll,
      userListRef,
      dismissGroup,
      loadSystemNotifications,
      groupAvatarUrls,
      getFullUrl,
      transferDialogRef,
      selectedCount,
      pagination,
      hoverMemberId,
      handleSearchInput,
      isUserInGroup,
      getAvatarPosition,
      getMemberAvatar,
      getMemberRole,
      getMemberName,
      getMemberId,
      getMemberKey,
      canRemoveMember,
      close,
      filteredTransferMembers,
      showTransferDialog,
      selectTransferMember,
      confirmTransfer,
      handleTransferSearch,
      showEditNameDialog,
      cancelEditName,
      confirmEditName,
      toggleMute,
      removeMember,
      exitGroup,
      showAddMemberDialog,
      closeAddMemberDialog,
      selectUser,
      isUserSelected,
      confirmAddMembers
    };
  }
};
</script>
<style scoped>
.group-info-dialog {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.group-info-content {
  background-color: white;
  width: 90%;
  max-width: 500px;
  border-radius: 12px;
  overflow: hidden;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.group-info-header {
  padding: 20px;
  text-align: center;
  position: relative;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}

.group-info-close {
  position: absolute;
  right: 20px;
  top: 20px;
  cursor: pointer;
  font-size: 18px;
  color: #999;
}

.group-info-avatar {
  width: 80px;
  height: 80px;
  border-radius: 10px;
  margin: 0 auto 15px;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f0f2f5;
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

.group-info-name {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.group-info-edit {
  margin-left: 8px;
  color: #1890ff;
  cursor: pointer;
  font-size: 16px;
}

.group-info-id {
  font-size: 14px;
  color: #999;
}

.group-info-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 200px;
}

.group-info-section {
  flex-shrink: 0;
}

.group-info-section-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 15px;
  color: #333;
}

.members-list {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
  max-height: 300px;
  overflow-y: auto;
  padding-right: 5px;
}

.member-item {
  text-align: center;
  position: relative;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.member-item:hover {
  transform: translateY(-2px);
}

.member-avatar-container {
  position: relative;
  width: 50px;
  height: 50px;
  margin: 0 auto 8px;
}

.member-avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  overflow: hidden;
  background-color: #f0f2f5;
}

.member-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.member-remove-action {
  position: absolute;
  top: -8px;
  left: -8px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background-color: #ff4d4f;
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 12px;
  cursor: pointer;
  z-index: 10;
  border: 2px solid white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  transition: all 0.2s ease;
}

.member-remove-action:hover {
  background-color: #d9363e;
  transform: scale(1.1);
}

.member-name {
  font-size: 12px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 4px;
}

.member-role {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}

.add-member-btn {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background-color: #f0f2f5;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #999;
  font-size: 24px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.add-member-btn:hover {
  background-color: #e6e6e6;
}

.group-info-actions {
  padding: 20px;
  border-top: 1px solid #eee;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
  flex-shrink: 0;
  background-color: white;
}

.group-action-btn {
  padding: 15px;
  text-align: center;
  background-color: #f0f2f5;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.group-action-btn:hover {
  background-color: #e6e6e6;
}

.danger-action {
  color: #ff4d4f;
  background-color: #fff2f0;
}

.danger-action:hover {
  background-color: #ffccc7;
}

/* 编辑名称弹窗 */
.edit-name-dialog {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1001;
}

.edit-name-content {
  background-color: white;
  width: 80%;
  max-width: 400px;
  border-radius: 12px;
  padding: 20px;
}

.edit-name-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 15px;
  text-align: center;
}

.edit-name-input {
  width: 100%;
  padding: 12px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 16px;
}

.edit-name-buttons {
  display: flex;
  justify-content: space-between;
}

.edit-name-btn {
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  border: none;
}

.edit-name-cancel {
  background-color: #f0f2f5;
  color: #333;
}

.edit-name-confirm {
  background-color: #1890ff;
  color: white;
}

/* 添加成员弹窗 */
.add-member-dialog {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1001;
}

.add-member-content {
  background-color: white;
  width: 90%;
  max-width: 500px;
  border-radius: 12px;
  overflow: hidden;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.add-member-header {
  padding: 20px;
  text-align: center;
  position: relative;
  border-bottom: 1px solid #eee;
}

.add-member-title {
  font-size: 18px;
  font-weight: bold;
}

.add-member-close {
  position: absolute;
  right: 20px;
  top: 20px;
  cursor: pointer;
  font-size: 18px;
  color: #999;
}

.add-member-search {
  padding: 15px;
  border-bottom: 1px solid #eee;
}

.search-input {
  width: 100%;
  padding: 10px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  font-size: 14px;
}

.add-member-list {
  flex: 1;
  overflow-y: auto;
  max-height: 300px;
}

.user-item {
  display: flex;
  align-items: center;
  padding: 12px 15px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
}

.user-item:hover {
  background-color: #f9f9f9;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  margin-right: 12px;
}

.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-info {
  flex: 1;
}

.user-name {
  font-weight: 500;
  margin-bottom: 2px;
}

.user-contact {
  font-size: 12px;
  color: #888;
  margin-top: 2px;
}

.user-checkbox {
  margin-left: 10px;
}

.user-item-disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.user-in-group-tag {
  font-size: 12px;
  color: #999;
  padding: 2px 6px;
  background-color: #f0f0f0;
  border-radius: 4px;
}

.no-users {
  text-align: center;
  padding: 20px;
  color: #999;
}

.loading-more,
.no-more {
  text-align: center;
  padding: 15px;
  color: #999;
  font-size: 14px;
}

.loading-more i {
  margin-right: 8px;
}

.add-member-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border-top: 1px solid #eee;
}

.selected-count {
  font-size: 14px;
  color: #666;
}

.add-member-buttons {
  display: flex;
  gap: 10px;
}

.add-member-cancel,
.add-member-confirm {
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  border: none;
}

.add-member-cancel {
  background-color: #f0f2f5;
  color: #333;
}

.add-member-confirm {
  background-color: #1890ff;
  color: white;
}

/* 滚动条样式 */
.members-list::-webkit-scrollbar,
.add-member-list::-webkit-scrollbar {
  width: 4px;
}

.members-list::-webkit-scrollbar-track,
.add-member-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 2px;
}

.members-list::-webkit-scrollbar-thumb,
.add-member-list::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 2px;
}

.members-list::-webkit-scrollbar-thumb:hover,
.add-member-list::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 响应式设计 */
@media (max-width: 480px) {
  .group-info-content {
    width: 95%;
    max-height: 85vh;
  }
  
  .members-list {
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    max-height: 250px;
  }
  
  .group-info-actions {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 15px;
  }
  
  .group-action-btn {
    padding: 12px;
    font-size: 13px;
  }
  
  .member-avatar-container {
    width: 45px;
    height: 45px;
  }
  
  .member-remove-action {
    width: 20px;
    height: 20px;
    font-size: 10px;
  }
  
  .group-info-body {
    padding: 15px;
    min-height: 150px;
  }
  
  .add-member-content {
    width: 95%;
  }
}

@media (max-height: 600px) {
  .group-info-content {
    max-height: 90vh;
  }
  
  .members-list {
    max-height: 200px;
  }
  
  .group-info-body {
    min-height: 120px;
  }
  
  .add-member-list {
    max-height: 250px;
  }
}

/* 群主转让弹窗样式 */
.transfer-dialog {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1002;
}

.transfer-content {
  background-color: white;
  width: 90%;
  max-width: 400px;
  border-radius: 12px;
  overflow: hidden;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.transfer-header {
  padding: 20px;
  text-align: center;
  position: relative;
  border-bottom: 1px solid #eee;
}

.transfer-title {
  font-size: 18px;
  font-weight: bold;
  color: #e67e22;
}

.transfer-close {
  position: absolute;
  right: 20px;
  top: 20px;
  cursor: pointer;
  font-size: 18px;
  color: #999;
}

.transfer-warning {
  background-color: #fff3e0;
  padding: 15px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #e67e22;
}

.transfer-warning i {
  font-size: 20px;
}

.transfer-search {
  padding: 15px;
  border-bottom: 1px solid #eee;
}

.transfer-search-input {
  width: 100%;
  padding: 10px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  font-size: 14px;
}

.transfer-members-list {
  flex: 1;
  overflow-y: auto;
  max-height: 300px;
  min-height: 100px; /* 增加最小高度确保即使没有内容也能看到区域 */
  padding: 10px;
}

.transfer-member-item {
  display: flex;
  align-items: center;
  padding: 12px;
  cursor: pointer;
  border-radius: 8px;
  transition: background-color 0.2s;
  margin-bottom: 8px;
}

.transfer-member-item:hover {
  background-color: #f5f5f5;
}

.transfer-member-item.selected {
  background-color: #e3f2fd;
  border: 1px solid #2196f3;
}

.transfer-member-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  margin-right: 12px;
}

.transfer-member-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.transfer-member-info {
  flex: 1;
}

.transfer-member-name {
  font-weight: 500;
  margin-bottom: 2px;
}

.transfer-member-role {
  font-size: 12px;
  color: #999;
}

.transfer-member-select {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid #ddd;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.transfer-member-item.selected .transfer-member-select {
  background-color: #2196f3;
  border-color: #2196f3;
}

.no-transfer-members {
  text-align: center;
  padding: 20px;
  color: #999;
}

.transfer-buttons {
  display: flex;
  padding: 15px;
  gap: 10px;
  border-top: 1px solid #eee;
}

.transfer-cancel,
.transfer-confirm {
  flex: 1;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  border: none;
  font-size: 14px;
}

.transfer-cancel {
  background-color: #f0f2f5;
  color: #333;
}

.transfer-confirm {
  background-color: #e67e22;
  color: white;
}

.transfer-confirm:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

/* 转让按钮样式 */
.transfer-action {
  color: #e67e22;
  background-color: #fff3e0;
}

.transfer-action:hover {
  background-color: #ffe0b2;
}

/* 响应式调整 */
@media (max-width: 480px) {
  .transfer-content {
    width: 95%;
  }
  
  .transfer-members-list {
    max-height: 250px;
  }
}

::v-deep .transfer-dialog {
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
  z-index: 9999 !important;
}


/* 确保弹窗内容容器正确显示 */
.transfer-content {
  /* 增加明显的边框便于调试 */
  border: 2px solid #e67e22 !important;
}

.transfer-dialog {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1002;
  visibility: visible !important;
  opacity: 1 !important;
}

.transfer-content {
  background-color: white;
  width: 90%;
  max-width: 400px;
  border-radius: 12px;
  overflow: hidden;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  animation: fadeIn 0.3s ease;
}

/* 添加关键帧动画 */
@keyframes fadeIn {
  from { 
    opacity: 0; 
    transform: translateY(-20px) scale(0.95); 
  }
  to { 
    opacity: 1; 
    transform: translateY(0) scale(1); 
  }
}

/* 确保弹窗在打开时可见 */
.transfer-dialog[style*="display: none"] {
  display: flex !important;
}

/* 调试用的高亮边框 */
.debug-border {
  border: 2px solid red !important;
}

</style>