import { createStore } from 'vuex';
import chatModule from './modules/chat';
import axios from 'axios';
import { ElMessage } from 'element-plus';
import { API_CONFIG } from '@/config/config';

// 从 localStorage 中恢复 Token 和用户信息
const token = localStorage.getItem("token");
const user = JSON.parse(localStorage.getItem("user"));

// 创建axios实例
const service = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: 10000,
});

// 是否正在刷新token的标志
let isRefreshing = false;
// 重试队列
let requests = [];

// 请求拦截器
service.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
service.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const { config, response } = error;
    
    if (response && response.status === 401) {
      // token过期
      if (!isRefreshing) {
        isRefreshing = true;
        
        try {
          // 调用刷新token接口
          const refreshResponse = await axios.post(
            `${API_CONFIG.BASE_URL}/refresh`,
            {},
            {
              headers: {
                Authorization: `Bearer ${localStorage.getItem('token')}`
              }
            }
          );
          
          if (refreshResponse.data.access_token) {
            const newToken = refreshResponse.data.access_token;
            // 更新store和localStorage中的token
            localStorage.setItem('token', newToken);
            
            // 重试所有队列中的请求
            requests.forEach(cb => cb(newToken));
            requests = [];
            
            // 重试当前请求
            config.headers.Authorization = `Bearer ${newToken}`;
            return service(config);
          }
        } catch (refreshError) {
          // 刷新token失败，跳转到登录页
          ElMessage.error('登录已过期，请重新登录');
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      } else {
        // 正在刷新token，将请求加入队列
        return new Promise((resolve) => {
          requests.push((token) => {
            config.headers.Authorization = `Bearer ${token}`;
            resolve(service(config));
          });
        });
      }
    }
    
    return Promise.reject(error);
  }
);

// 导出axios实例供其他模块使用
export const axiosInstance = service;

export default createStore({
  modules: {
    chat: chatModule,
  },

  state: {
    user: user || null, // 存储用户信息
    token: token || null, // 存储 Token，初始化时从 localStorage 中恢复
  },
  mutations: {
    // 设置用户信息
    setUser(state, user) {
      state.user = user;
      localStorage.setItem("user", JSON.stringify(user)); // 将用户信息存储到 localStorage
    },
    // 设置 Token
    setToken(state, token) {
      state.token = token;
      localStorage.setItem("token", token); // 将 Token 存储到 localStorage
    },
    // 清除用户信息
    clearUser(state) {
      state.user = null;
      localStorage.removeItem("user"); // 清除 localStorage 中的用户信息
    },
    // 清除 Token
    clearToken(state) {
      state.token = null;
      localStorage.removeItem("token"); // 清除 localStorage 中的 Token
    },
    // 更新用户信息
    updateUser(state, user) {
      state.user = { ...state.user, ...user }; // 合并用户信息
      localStorage.setItem("user", JSON.stringify(state.user)); // 更新 localStorage
    }
  },
  actions: {
    // 登录
    login({ commit }, { user, token }) {
      commit('setUser', user);
      commit('setToken', token);
    },
    // 退出登录
    logout({ commit }) {
      commit('clearUser');
      commit('clearToken');
      commit('CLEAR_ALL_CHATS');
    },
    // 更新用户信息
    updateUser({ commit }, user) {
      commit('updateUser', user);
    },
    // 刷新token
    async refreshToken({ commit, state }) {
      try {
        const response = await service.post('/refresh', {}, {
          headers: {
            Authorization: `Bearer ${state.token}`
          }
        });
        
        if (response.data.access_token) {
          commit('setToken', response.data.access_token);
          return response.data.access_token;
        }
      } catch (error) {
        commit('clearUser');
        commit('clearToken');
        commit('CLEAR_ALL_CHATS');
        throw error;
      }
    }
  },
  getters: {
    // 获取用户信息
    user: (state) => state.user,
    // 获取 Token
    token: (state) => state.token,
    // 获取axios实例
    axios: () => service
  },
});