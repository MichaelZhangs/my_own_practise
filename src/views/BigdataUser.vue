<template>
  <div class="bigdata-container">
    <!-- 查询表单 --> 
    <div class="search-card">
      <h2>大数据用户查询</h2>
      <div class="search-form">
        <div class="form-group">
          <label>姓名：</label>
          <input v-model="searchParams.name" placeholder="输入姓名" />
        </div>
        <div class="form-group">
          <label>证件号：</label>
          <input v-model="searchParams.idno" placeholder="输入证件号" />
        </div>
        <div class="form-group">
          <label>性别：</label>
          <select v-model="searchParams.sex">
            <option value="">全部</option>
            <option value="男">男</option>
            <option value="女">女</option>
          </select>
        </div>
        <div class="form-group">
          <label>省份：</label>
          <input v-model="searchParams.province" placeholder="输入省份" />
        </div>
        <div class="form-group age-range">
          <label>年龄范围：</label>
          <input 
            v-model.number="searchParams.min_age" 
            type="number" 
            placeholder="最小" 
            min="0"
          />
          <span>-</span>
          <input 
            v-model.number="searchParams.max_age" 
            type="number" 
            placeholder="最大" 
            min="0"
          />
        </div>
        <button class="search-btn" @click="fetchData">查询</button>
        <button class="reset-btn" @click="resetSearch">重置</button>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="data-table">
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="error" class="error">
        {{ error }}
        <button @click="fetchData">重试</button>
      </div>
      <template v-else>
        <table>
          <thead>
            <tr>
              <th>姓名</th>
              <th>证件号</th>
              <th>性别</th>
              <th>出生地</th>
              <th>证件类型</th>
              <th>省份</th>
              <th>年龄</th>
              <th>生日</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.idno">
              <td>{{ user.name || '-' }}</td>
              <td>{{ user.idno || '-' }}</td>
              <td>{{ user.sex || '-' }}</td>
              <td>{{ user.bplace || '-' }}</td>
              <td>{{ user.idtype || '-' }}</td>
              <td>{{ user.province || '-' }}</td>
              <td>{{ user.age ?? '-' }}</td>
              <td>{{ formatBirthday(user.birthday) }}</td>
            </tr>
          </tbody>
        </table>

        <!-- 分页控件 -->
        <div class="pagination">
          <button 
            @click="prevPage" 
            :disabled="pagination.page === 1"
          >
            上一页
          </button>
          <span class="page-info">
            第 {{ pagination.page }} 页 / 共 {{ pagination.total_pages }} 页 
            (共 {{ pagination.total }} 条记录)
          </span>
          <button 
            @click="nextPage" 
            :disabled="pagination.page >= pagination.total_pages"
          >
            下一页
          </button>
          <select v-model="pagination.page_size" @change="handlePageSizeChange">
            <option value="50">50条/页</option>
            <option value="100">100条/页</option>
            <option value="200">200条/页</option>
          </select>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import axios from 'axios'
import { API_CONFIG } from '@/config/config'
import { debounce } from 'lodash'

// 用户数据
const users = ref([])
const loading = ref(false)
const error = ref(null)

// 查询参数
const searchParams = reactive({
  name: '',
  idno: '',
  sex: '',
  province: '',
  min_age: null,
  max_age: null
})

// 分页参数
const pagination = reactive({
  page: 1,
  page_size: 100,
  total: 0,
  total_pages: 1
})

// 格式化生日显示
const formatBirthday = (birthday) => {
  if (!birthday) return '-'
  const dateStr = birthday.toString()
  if (dateStr.length === 8) {
    return `${dateStr.substring(0,4)}-${dateStr.substring(4,6)}-${dateStr.substring(6,8)}`
  }
  return birthday
}

// 获取数据
const fetchData = async () => {
  try {
    loading.value = true
    error.value = null
    
    const params = {
      ...searchParams,
      page: pagination.page,
      page_size: pagination.page_size
    }

    // 清除空参数
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null) {
        delete params[key]
      }
    })

    const response = await axios.get(`${API_CONFIG.BASE_URL}/bigdata/bigdata-users`,  {
      params,
      headers: {
        'Cache-Control': 'no-cache' // 明确禁用缓存
      }
      })
    users.value = response.data.data
    pagination.total = response.data.total
    pagination.total_pages = Math.ceil(response.data.total / pagination.page_size)
    
  } catch (err) {
    console.error('获取数据失败:', err)
    error.value = err.response?.data?.detail || err.message || '获取数据失败'
  } finally {
    loading.value = false
  }
}

// 重置查询
const resetSearch = () => {
  Object.assign(searchParams, {
    name: '',
    idno: '',
    sex: '',
    province: '',
    min_age: null,
    max_age: null
  })
  pagination.page = 1
  fetchData()
}

// 分页操作
const prevPage = () => {
  if (pagination.page > 1) {
    pagination.page--
    fetchData()
  }
}

const nextPage = () => {
  if (pagination.page < pagination.total_pages) {
    pagination.page++
    fetchData()
  }
}

const handlePageSizeChange = () => {
  pagination.page = 1
  fetchData()
}

// 使用 debounce 优化实时查询
const debouncedFetchData = debounce(fetchData, 500)

watch(searchParams, () => {
  debouncedFetchData()
}, { deep: true })

// 初始化加载数据
onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.bigdata-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  font-family: 'Arial', sans-serif;
}

.search-card {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.search-card h2 {
  margin-top: 0;
  color: #333;
  border-bottom: 1px solid #e6e6e6;
  padding-bottom: 10px;
}

.search-form {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
  align-items: end;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  margin-bottom: 5px;
  font-weight: bold;
  color: #666;
}

.form-group input,
.form-group select {
  padding: 8px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
}

.age-range {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 5px;
}

.age-range input {
  width: 60px;
}

.search-btn, .reset-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.search-btn {
  background-color: #409eff;
  color: white;
}

.search-btn:hover {
  background-color: #66b1ff;
}

.reset-btn {
  background-color: #f5f5f5;
  color: #666;
  margin-left: 10px;
}

.reset-btn:hover {
  background-color: #e6e6e6;
}

.data-table {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.loading, .error {
  text-align: center;
  padding: 20px;
  color: #666;
}

.error {
  color: #f56c6c;
}

.error button {
  margin-top: 10px;
  padding: 5px 10px;
  background: #f56c6c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 20px;
}

th, td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #ebeef5;
}

th {
  background-color: #f5f7fa;
  color: #333;
  font-weight: bold;
}

tr:hover {
  background-color: #f5f7fa;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  margin-top: 20px;
}

.pagination button {
  padding: 6px 12px;
  background: white;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  cursor: pointer;
}

.pagination button:disabled {
  color: #c0c4cc;
  cursor: not-allowed;
}

.pagination select {
  padding: 6px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

.page-info {
  color: #666;
}

@media (max-width: 768px) {
  .search-form {
    grid-template-columns: 1fr;
  }
  
  table {
    display: block;
    overflow-x: auto;
  }
}
</style>