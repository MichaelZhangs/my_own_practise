<template>
  <div class="user-list-container">
    <h2>用户列表</h2>
    <!-- 查询框 -->
    <div class="search-box">
      <input
        v-model="searchQuery.username"
        placeholder="用户名"
        class="search-input"
      />
      <input
        v-model="searchQuery.phone"
        placeholder="手机号"
        class="search-input"
      />
      <select v-model="searchQuery.sex" class="search-select">
        <option value="">全部性别</option>
        <option value="male">男</option>
        <option value="female">女</option>
        <option value="other">其他</option>
      </select>
      <button @click="fetchUsers" class="search-button">查询</button>
    </div>

    <!-- 用户列表表格 -->
    <table class="user-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>用户名</th>
          <th>手机号</th>
          <th>性别</th>
          <th>头像</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td>{{ user.id }}</td>
          <td>{{ user.username }}</td>
          <td>{{ user.phone }}</td>
          <td>{{ sexMap[user.sex] || '未知' }}</td> <!-- 映射性别 -->
          <td>
            <img
              :src="user.photo ? `http://127.0.0.1:8000${user.photo}` : defaultAvatar"
              alt="头像"
              class="user-avatar"
            />
          </td>
        </tr>
      </tbody>
    </table>

    <!-- 分页组件 -->
    <div class="pagination">
      <button
        @click="prevPage"
        :disabled="currentPage === 1"
        class="pagination-button"
      >
        上一页
      </button>
      <span class="pagination-info">
        第 {{ currentPage }} 页 / 共 {{ totalPages }} 页
      </span>
      <button
        @click="nextPage"
        :disabled="currentPage === totalPages"
        class="pagination-button"
      >
        下一页
      </button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed, watch } from 'vue';
import axios from 'axios';
import defaultAvatar from '@/assets/default-avatar.png'; // 默认头像
import { debounce } from 'lodash'; // 引入 lodash 的防抖函数
import { API_CONFIG } from '@/config/config';

export default {
  name: 'UserList',
  setup() {
    const users = ref([]); // 所有用户数据
    const totalCount = ref(0); // 总数据量
    const searchQuery = ref({
      username: '',
      phone: '',
      sex: '',
    }); // 查询条件
    const currentPage = ref(1); // 当前页码
    const pageSize = 10; // 每页显示的数据量

    // 性别映射字典
    const sexMap = {
      male: '男',
      female: '女',
      other: '其他',
    };

    // 获取用户列表
    const fetchUsers = async () => {
      try {
        const response = await axios.get(`${API_CONFIG.BASE_URL}/user/get-users`, {
          params: {
            username: searchQuery.value.username,
            phone: searchQuery.value.phone,
            sex: searchQuery.value.sex,
            page: currentPage.value,
            page_size: pageSize,
          },
        });
        users.value = response.data.data; // 更新用户数据
        totalCount.value = response.data.total; // 更新总数据量
      } catch (error) {
        console.error('获取用户列表失败:', error);
      }
    };

    // 防抖处理后的 fetchUsers
    const debouncedFetchUsers = debounce(fetchUsers, 300); // 300ms 防抖

    // 监听 searchQuery 的变化
    watch(
      searchQuery,
      () => {
        currentPage.value = 1; // 重置到第一页
        debouncedFetchUsers(); // 触发防抖查询
      },
      { deep: true } // 深度监听
    );

    // 总页数
    const totalPages = computed(() => {
      return Math.ceil(totalCount.value / pageSize);
    });

    // 上一页
    const prevPage = () => {
      if (currentPage.value > 1) {
        currentPage.value--;
        fetchUsers(); // 重新获取数据
      }
    };

    // 下一页
    const nextPage = () => {
      if (currentPage.value < totalPages.value) {
        currentPage.value++;
        fetchUsers(); // 重新获取数据
      }
    };

    // 页面加载时获取用户列表
    onMounted(() => {
      fetchUsers();
    });

    return {
      users,
      searchQuery,
      currentPage,
      totalPages,
      prevPage,
      nextPage,
      fetchUsers,
      defaultAvatar,
      sexMap, // 返回性别映射字典
    };
  },
};
</script>

<style scoped>
.user-list-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

h2 {
  text-align: center;
  margin-bottom: 20px;
}

.search-box {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.search-input {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  flex: 1;
}

.search-select {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.search-button {
  padding: 8px 16px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.search-button:hover {
  background-color: #40a9ff;
}

.user-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 20px;
}

.user-table th,
.user-table td {
  padding: 12px;
  border: 1px solid #ddd;
  text-align: left;
}

.user-table th {
  background-color: #f5f5f5;
  font-weight: bold;
}

.user-table tr:hover {
  background-color: #f9f9f9;
}

.user-avatar {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  object-fit: cover;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
}

.pagination-button {
  padding: 8px 16px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.pagination-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.pagination-info {
  font-size: 14px;
  color: #666;
}
</style>